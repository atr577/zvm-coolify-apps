import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Loader2, ArrowLeft, ArrowRight, Play, RotateCcw, Image, Video, Wand2,
  ChevronDown, ChevronUp, AlertCircle, CheckCircle2, Trophy, Plus, Music, Volume2,
} from 'lucide-react'
import { discoverApi } from '@/services/api'
import type { DiscoverProject } from '@/types'
import { getErrorMessage } from '@/types'
import { RoundView } from '@/components/discover/RoundView'
import { PromptRefinement } from '@/components/discover/PromptRefinement'
import AudioSelection from '@/components/discover/AudioSelection'
import { getMediaUrl } from '@/utils/video'
import { getModelDisplayName, IMAGE_MODELS, VIDEO_MODELS, getDurationOptions } from '@/constants/models'

const POLL_INTERVAL = 3000

const STAGE_LABELS: Record<string, string> = {
  refine: 'Prompt Refinement',
  images: 'Image Exploration',
  videos: 'Video Exploration',
  audio: 'Audio Selection',
  extraction: 'Template Extraction',
  completed: 'Completed',
}

const STAGE_ICONS: Record<string, typeof Image> = {
  images: Image,
  videos: Video,
  extraction: Wand2,
  completed: CheckCircle2,
}

export default function DiscoverPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const projectId = Number(id)

  const [project, setProject] = useState<DiscoverProject | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [advancing, setAdvancing] = useState(false)
  const [rollingBack, setRollingBack] = useState(false)
  const [collapsedRounds, setCollapsedRounds] = useState<Set<number>>(new Set())
  const [selectedImageModel, setSelectedImageModel] = useState<string>(IMAGE_MODELS[0].value)
  const [selectedVideoModel, setSelectedVideoModel] = useState<string>(VIDEO_MODELS[0].value)
  const [selectedDuration, setSelectedDuration] = useState<string>('9')
  const [itemCount, setItemCount] = useState(4)
  const [pendingSelections, setPendingSelections] = useState<Record<number, Record<string, 'selected' | 'rejected'>>>({})
  const [feedback, setFeedback] = useState('')
  const [imageFinalistId, setImageFinalistId] = useState<number | null>(null)
  const [videoFinalistId, setVideoFinalistId] = useState<number | null>(null)
  const [creatingTemplate, setCreatingTemplate] = useState(false)
  const [audioVariantId, setAudioVariantId] = useState<number | null>(null)
  const [confirmingAudio, setConfirmingAudio] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchProject = useCallback(async () => {
    try {
      const res = await discoverApi.get(projectId)
      setProject(res.data)
      setError(null)
      return res.data
    } catch (err) {
      setError(getErrorMessage(err))
      return null
    }
  }, [projectId])

  // Initial load
  useEffect(() => {
    setLoading(true)
    fetchProject().finally(() => setLoading(false))
  }, [fetchProject])

  // Initialize model selectors from project data
  useEffect(() => {
    if (project?.image_model) {
      setSelectedImageModel(project.image_model)
    }
    if (project?.video_model) {
      setSelectedVideoModel(project.video_model)
    }
    if (project?.video_duration) {
      setSelectedDuration(project.video_duration)
    }
  }, [project?.image_model, project?.video_model, project?.video_duration])

  // Polling when items are generating
  useEffect(() => {
    const needsPolling = project?.rounds.some(r =>
      r.status === 'generating' || r.items.some(i => i.status === 'pending' || i.status === 'generating')
    )

    if (needsPolling) {
      pollRef.current = setInterval(fetchProject, POLL_INTERVAL)
    } else if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [project, fetchProject])

  const handleSelectionsChange = useCallback((roundId: number, selections: Record<string, 'selected' | 'rejected'>) => {
    setPendingSelections(prev => ({ ...prev, [roundId]: selections }))
  }, [])

  // Auto-submit all pending selections to backend
  const submitAllSelections = async (): Promise<boolean> => {
    const entries = Object.entries(pendingSelections)
    if (entries.length === 0) return true
    try {
      for (const [roundId, selections] of entries) {
        if (Object.keys(selections).length === 0) continue
        await discoverApi.submitSelection(projectId, Number(roundId), {
          selections,
          feedback: feedback || undefined,
        })
      }
      setPendingSelections({})
      setFeedback('')
      return true
    } catch (err) {
      setError(getErrorMessage(err))
      return false
    }
  }

  const handleGenerateRound = async () => {
    setGenerating(true)
    setError(null)
    try {
      // Auto-submit selections before generating
      const ok = await submitAllSelections()
      if (!ok) return
      const model = project?.stage === 'videos' ? selectedVideoModel : selectedImageModel
      const duration = project?.stage === 'videos' ? selectedDuration : undefined
      await discoverApi.generateRound(projectId, feedback || undefined, model, itemCount, duration)
      setFeedback('')
      await fetchProject()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  const doAdvanceToVideo = async (finalistId: number) => {
    setAdvancing(true)
    setError(null)
    try {
      await discoverApi.advanceToVideo(projectId, finalistId)
      setImageFinalistId(null)
      await fetchProject()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAdvancing(false)
    }
  }

  const handleAdvanceToAudio = async () => {
    if (!project || !videoFinalistId) return
    setAdvancing(true)
    setError(null)
    try {
      // Auto-submit selections before advancing
      const ok = await submitAllSelections()
      if (!ok) {
        setAdvancing(false)
        return
      }

      await discoverApi.advanceToAudio(projectId, videoFinalistId)
      setVideoFinalistId(null)
      await fetchProject()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAdvancing(false)
    }
  }

  const handleCreateAnotherTemplate = async () => {
    if (!project) return
    setCreatingTemplate(true)
    setError(null)
    try {
      // Get winning video prompt
      const finalistVideo = project.rounds
        .filter(r => r.round_type === 'video')
        .flatMap(r => r.items)
        .find(i => i.id === project.finalist_video_item_id)
      const videoPrompt = finalistVideo?.prompt || ''

      const res = await discoverApi.createTemplate(projectId, {
        name: project.name,
        platforms: ['youtube', 'instagram', 'tiktok'],
        video_template_prompt: videoPrompt,
      })
      navigate(`/?project=${res.data.project_id}`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setCreatingTemplate(false)
    }
  }

  const toggleRoundCollapse = (roundId: number) => {
    setCollapsedRounds(prev => {
      const next = new Set(prev)
      if (next.has(roundId)) {
        next.delete(roundId)
      } else {
        next.add(roundId)
      }
      return next
    })
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Project not found</h3>
        <button onClick={() => navigate('/dashboard')} className="text-purple-600 hover:text-purple-800">
          Back to Dashboard
        </button>
      </div>
    )
  }

  const StageIcon = STAGE_ICONS[project.stage] || Image
  const currentRounds = project.rounds
    .filter(r =>
      project.stage === 'images' ? r.round_type === 'image' :
      project.stage === 'videos' ? r.round_type === 'video' :
      project.stage === 'audio' ? r.round_type === 'video' :
      true
    )
    .sort((a, b) => {
      const typeOrder = { image: 0, video: 1 }
      const ta = typeOrder[a.round_type as keyof typeof typeOrder] ?? 2
      const tb = typeOrder[b.round_type as keyof typeof typeOrder] ?? 2
      if (ta !== tb) return ta - tb
      return a.round_number - b.round_number
    })
  const latestRound = currentRounds.length > 0 ? currentRounds[currentRounds.length - 1] : null
  const isGenerating = latestRound?.items.some(i => i.status === 'pending' || i.status === 'generating') || false
  const isActiveStage = project.stage !== 'audio' && project.stage !== 'extraction' && project.stage !== 'completed'
  const showRefinement = project.stage === 'images' && currentRounds.length === 0

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/dashboard')}
          className="text-gray-400 hover:text-gray-600"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <p className="text-sm text-gray-500 mt-1">{project.concept}</p>
        </div>
        <div className="flex items-center gap-2">
          <StageIcon className="h-5 w-5 text-purple-600" />
          <span className="text-sm font-medium text-purple-600">{showRefinement ? STAGE_LABELS.refine : STAGE_LABELS[project.stage]}</span>
        </div>
      </div>

      {/* Stage progress */}
      <div className="mb-6">
        <div className="flex items-center gap-1">
          {['refine', 'images', 'videos', 'audio', 'completed'].map((stage, idx) => {
            const stages = ['refine', 'images', 'videos', 'audio', 'completed']
            const displayStage = project.stage === 'extraction' ? 'completed'
              : showRefinement ? 'refine'
              : project.stage
            const currentIdx = stages.indexOf(displayStage)
            const isActive = idx === currentIdx
            const isPast = idx < currentIdx
            return (
              <div key={stage} className="flex-1 h-1.5 rounded-full" style={{
                backgroundColor: isPast || (isActive && stage === 'completed')
                  ? '#9333ea' // purple-600
                  : isActive
                  ? '#a855f7' // purple-400
                  : '#e5e7eb'  // gray-200
              }} />
            )
          })}
        </div>
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>Refine</span>
          <span>Images</span>
          <span>Videos</span>
          <span>Audio</span>
          <span>Done</span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
            &times;
          </button>
        </div>
      )}

      {/* Final Result (extraction + completed — same UI, two states) */}
      {(project.stage === 'extraction' || project.stage === 'completed') && (() => {
        const finalistVideo = project.rounds
          .filter(r => r.round_type === 'video')
          .flatMap(r => r.items)
          .find(i => i.id === project.finalist_video_item_id)
        const finalistImage = project.rounds
          .filter(r => r.round_type === 'image')
          .flatMap(r => r.items)
          .find(i => i.id === project.finalist_image_item_id)
        const selectedAudio = project.selected_audio_variant_id
          ? (project.audio_variants || []).find(v => v.id === project.selected_audio_variant_id)
          : null
        const videoSrc = project.merged_video_url
          || (finalistVideo ? getMediaUrl(finalistVideo.local_path, finalistVideo.result_url) : null)
        const isCompleted = project.stage === 'completed'
        const borderColor = isCompleted ? 'border-green-200' : 'border-purple-200'
        const bgColor = isCompleted ? 'bg-green-50' : 'bg-purple-50'
        const textColor = isCompleted ? 'text-green-800' : 'text-purple-800'
        const subColor = isCompleted ? 'text-green-500' : 'text-purple-500'
        const IconComp = isCompleted ? CheckCircle2 : Trophy
        const iconColor = isCompleted ? 'text-green-600' : 'text-purple-600'

        return (
          <div className={`bg-white border ${borderColor} rounded-xl overflow-hidden mb-6`}>
            <div className={`${bgColor} px-5 py-3 flex items-center gap-2`}>
              <IconComp className={`h-4 w-4 ${iconColor}`} />
              <span className={`text-sm font-semibold ${textColor}`}>
                {isCompleted ? 'Discovery Complete — Template Created' : 'Final Result'}
              </span>
              {project.merged_video_url && (
                <span className={`ml-auto text-xs ${subColor}`}>Video + Audio merged</span>
              )}
            </div>
            <div className="p-5 flex gap-5">
              {/* Video preview */}
              {videoSrc && (
                <div className="flex-shrink-0 w-40">
                  <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
                    <video
                      src={videoSrc}
                      controls
                      playsInline
                      preload="metadata"
                      className="w-full h-full object-contain"
                    />
                  </div>
                </div>
              )}
              {/* Prompts */}
              <div className="min-w-0 flex-1 space-y-3">
                {finalistImage && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Image Prompt</p>
                    <p className="text-sm text-gray-700">{finalistImage.prompt}</p>
                  </div>
                )}
                {finalistVideo && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Video Prompt</p>
                    <p className="text-sm text-gray-700">{finalistVideo.prompt}</p>
                  </div>
                )}
                {selectedAudio && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                      Audio ({selectedAudio.audio_type === 'sfx' ? 'SFX' : 'Music'})
                    </p>
                    <p className="text-sm text-gray-700">
                      {selectedAudio.prompt || 'Auto-generated'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })()}

      {/* Finalist reference (video stage only) */}
      {project.stage === 'videos' && project.finalist_image_item_id && (() => {
        const finalistItem = project.rounds
          .filter(r => r.round_type === 'image')
          .flatMap(r => r.items)
          .find(i => i.id === project.finalist_image_item_id)
        if (!finalistItem) return null
        const imgUrl = getMediaUrl(finalistItem.local_path, finalistItem.result_url)
        return (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <div className="flex gap-4">
              {imgUrl && (
                <img src={imgUrl} alt="Finalist" className="w-24 h-24 rounded-lg object-cover flex-shrink-0" />
              )}
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Trophy className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-semibold text-amber-800">Image Finalist</span>
                </div>
                <p className="text-xs text-amber-700 line-clamp-4">{finalistItem.prompt}</p>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Audio Selection */}
      {project.stage === 'audio' && (
        <AudioSelection project={project} onRefresh={fetchProject} onVariantSelect={setAudioVariantId} />
      )}

      {/* Prompt Refinement (before first image round) */}
      {showRefinement && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <PromptRefinement
            projectId={projectId}
            onReady={() => handleGenerateRound()}
            generating={generating}
          />
        </div>
      )}

      {/* Audio Action Bar */}
      {project.stage === 'audio' && (() => {
        const selectedVariant = audioVariantId
          ? (project.audio_variants || []).find(v => v.id === audioVariantId)
          : null
        const canConfirm = selectedVariant && selectedVariant.status === 'completed' && !(
          selectedVariant.audio_type !== 'sfx' &&
          !selectedVariant.hook_start_ms &&
          selectedVariant.detected_hooks &&
          selectedVariant.detected_hooks.length > 1
        )
        return (
          <div className="sticky bottom-0 z-20 bg-white border-t border-gray-200 -mx-6 px-6 py-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] mt-6">
            <div className="flex items-center justify-between gap-3">
              <button
                onClick={async () => {
                  setError(null)
                  setRollingBack(true)
                  try {
                    await discoverApi.rollbackAudio(projectId)
                    await fetchProject()
                  } catch (err) {
                    setError(getErrorMessage(err))
                  } finally {
                    setRollingBack(false)
                  }
                }}
                disabled={rollingBack}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                {rollingBack ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowLeft className="h-4 w-4" />}
                Back to Videos
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={async () => {
                    setError(null)
                    try {
                      await discoverApi.skipAudio(projectId)
                      await fetchProject()
                    } catch (err) {
                      setError(getErrorMessage(err))
                    }
                  }}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Skip Audio
                  <ArrowRight className="h-4 w-4" />
                </button>
                {canConfirm && (
                  <button
                    onClick={async () => {
                      if (!audioVariantId) return
                      setError(null)
                      setConfirmingAudio(true)
                      try {
                        await discoverApi.confirmAudio(projectId, audioVariantId)
                        await fetchProject()
                      } catch (err) {
                        setError(getErrorMessage(err))
                      } finally {
                        setConfirmingAudio(false)
                      }
                    }}
                    disabled={confirmingAudio}
                    className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    {confirmingAudio ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Merging...</>
                    ) : (
                      <><CheckCircle2 className="h-4 w-4" /> Confirm & Continue</>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        )
      })()}

      {/* Rounds */}
      {!showRefinement && project.stage !== 'audio' && <div className="space-y-6">
          {currentRounds.map((round, idx) => {
            const isLatest = idx === currentRounds.length - 1 && project.stage !== 'completed'
            const isCollapsed = collapsedRounds.has(round.id)

            return (
              <div key={round.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Collapsible header */}
                <button
                  onClick={() => toggleRoundCollapse(round.id)}
                  className="w-full flex items-center justify-between px-6 py-3 bg-gray-50 hover:bg-gray-100 transition"
                >
                  <span className="text-sm font-medium text-gray-700">
                    Round {round.round_number} ({round.round_type})
                    {round.model_used && (
                      <span className="text-gray-400 font-normal"> | {getModelDisplayName(round.model_used)}</span>
                    )}
                    {' '}&mdash; {round.selected_count} selected, {round.rejected_count} rejected
                  </span>
                  {isCollapsed ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronUp className="h-4 w-4 text-gray-400" />}
                </button>

                {!isCollapsed && (
                  <div className="p-6">
                    <RoundView
                      projectId={projectId}
                      round={round}
                      isLatestRound={isLatest}
                      onRefresh={fetchProject}
                      onSelectionsChange={handleSelectionsChange}
                      finalistItemId={
                        round.round_type === 'image' ? (imageFinalistId || project.finalist_image_item_id) :
                        round.round_type === 'video' ? (videoFinalistId || project.finalist_video_item_id) :
                        null
                      }
                      onCrownClick={round.round_type === 'video' ? setVideoFinalistId : setImageFinalistId}
                      readOnly={project.stage === 'extraction' || project.stage === 'completed'}
                    />
                  </div>
                )}
              </div>
            )
          })}

          {/* Audio section (extraction/completed — read-only, like a round) */}
          {(project.stage === 'extraction' || project.stage === 'completed') && (() => {
            const selectedAudio = project.selected_audio_variant_id
              ? (project.audio_variants || []).find(v => v.id === project.selected_audio_variant_id)
              : null
            if (!selectedAudio) return null
            const isAudioCollapsed = collapsedRounds.has(-1) // use -1 as synthetic ID for audio
            const formatMs = (ms: number) => {
              const s = Math.floor(ms / 1000)
              const m = Math.floor(s / 60)
              return `${m}:${String(s % 60).padStart(2, '0')}`
            }
            return (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => toggleRoundCollapse(-1)}
                  className="w-full flex items-center justify-between px-6 py-3 bg-gray-50 hover:bg-gray-100 transition"
                >
                  <span className="text-sm font-medium text-gray-700">
                    Audio — {selectedAudio.audio_type === 'sfx' ? 'Sound FX' : 'Music'} (selected)
                  </span>
                  {isAudioCollapsed ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronUp className="h-4 w-4 text-gray-400" />}
                </button>

                {!isAudioCollapsed && (
                  <div className="p-6 space-y-4">
                    {/* Prompt */}
                    {selectedAudio.prompt && (
                      <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                        <div className="flex items-start gap-2">
                          <Music className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
                          <p className="text-sm text-purple-700">{selectedAudio.prompt}</p>
                        </div>
                      </div>
                    )}

                    {/* Hook player */}
                    {selectedAudio.trimmed_file_url && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Volume2 className="h-4 w-4 text-gray-500" />
                          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Hook</span>
                          {selectedAudio.hook_start_ms != null && selectedAudio.hook_end_ms != null && (
                            <span className="text-xs text-gray-400">
                              {formatMs(selectedAudio.hook_start_ms)} – {formatMs(selectedAudio.hook_end_ms)}
                            </span>
                          )}
                          {selectedAudio.duration_ms != null && (
                            <span className="text-xs text-gray-400">
                              · {(selectedAudio.duration_ms / 1000).toFixed(1)}s
                            </span>
                          )}
                        </div>
                        <audio src={selectedAudio.trimmed_file_url} controls preload="metadata" className="w-full h-10" />
                      </div>
                    )}

                    {/* Full track player */}
                    {selectedAudio.file_url && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Music className="h-4 w-4 text-gray-500" />
                          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Full Track</span>
                          {selectedAudio.full_duration_ms != null && (
                            <span className="text-xs text-gray-400">
                              · {(selectedAudio.full_duration_ms / 1000).toFixed(1)}s
                            </span>
                          )}
                        </div>
                        <audio src={selectedAudio.file_url} controls preload="metadata" className="w-full h-10" />
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })()}

          {/* Action bar — sticky at bottom */}
          <div className="sticky bottom-0 z-20 bg-white border-t border-gray-200 -mx-6 px-6 py-4 space-y-3 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
              {/* Feedback / direction textarea */}
              {isActiveStage && (
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder={
                    project.stage === 'videos' && currentRounds.length === 0
                      ? "Describe what should happen in the video (e.g. 'object slowly descends, pause for suspense, violent pull inward — sparks fly')..."
                      : project.stage === 'videos'
                      ? "Feedback for next round (e.g. 'more dramatic destruction', 'slower build-up')..."
                      : currentRounds.length === 0
                      ? "Optional: describe what you're looking for..."
                      : "Optional feedback for next round (e.g. 'more dramatic lighting', 'closer to #3')..."
                  }
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                />
              )}

              <div className="flex items-center justify-between gap-3">
                {/* LEFT: Back navigation */}
                <div className="flex items-center gap-2">
                  {/* Back to Audio (extraction/completed) */}
                  {(project.stage === 'extraction' || project.stage === 'completed') && (
                    <button
                      onClick={async () => {
                        setRollingBack(true)
                        setError(null)
                        try {
                          await discoverApi.rollbackExtraction(projectId)
                          await fetchProject()
                        } catch (err) {
                          setError(getErrorMessage(err))
                        } finally {
                          setRollingBack(false)
                        }
                      }}
                      disabled={rollingBack}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                    >
                      {rollingBack ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowLeft className="h-4 w-4" />}
                      Back to Audio
                    </button>
                  )}
                  {/* Back to Refine (images stage) */}
                  {project.stage === 'images' && currentRounds.length > 0 && isActiveStage && (
                    <button
                      onClick={async () => {
                        if (!confirm('Go back to prompt refinement? All generated rounds will be deleted.')) return
                        setRollingBack(true)
                        setError(null)
                        try {
                          for (let i = 0; i < currentRounds.length; i++) {
                            await discoverApi.rollback(projectId)
                          }
                          setPendingSelections({})
                          setImageFinalistId(null)
                          setFeedback('')
                          await fetchProject()
                        } catch (err) {
                          setError(getErrorMessage(err))
                        } finally {
                          setRollingBack(false)
                        }
                      }}
                      disabled={rollingBack || generating}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                    >
                      {rollingBack ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowLeft className="h-4 w-4" />}
                      Back to Refine
                    </button>
                  )}
                </div>

                {/* RIGHT: Actions */}
                <div className="flex items-center gap-2 flex-wrap justify-end">
                  {/* Selectors */}
                  {isActiveStage && (
                    <select
                      value={project.stage === 'videos' ? selectedVideoModel : selectedImageModel}
                      onChange={(e) => {
                        if (project.stage === 'videos') setSelectedVideoModel(e.target.value)
                        else setSelectedImageModel(e.target.value)
                      }}
                      className="px-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    >
                      {(project.stage === 'videos' ? VIDEO_MODELS : IMAGE_MODELS).map(m => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  )}
                  {isActiveStage && project.stage === 'videos' && (
                    <select
                      value={selectedDuration}
                      onChange={(e) => setSelectedDuration(e.target.value)}
                      className="px-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    >
                      {getDurationOptions(selectedVideoModel).map(d => (
                        <option key={d.value} value={d.value}>{d.label}</option>
                      ))}
                    </select>
                  )}
                  {isActiveStage && (
                    <select
                      value={itemCount}
                      onChange={(e) => setItemCount(Number(e.target.value))}
                      className="px-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    >
                      {[1, 2, 3, 4, 5, 6, 7].map(n => (
                        <option key={n} value={n}>{n} {n === 1 ? 'variant' : 'variants'}</option>
                      ))}
                    </select>
                  )}

                  {/* Regenerate (amber) */}
                  {currentRounds.length > 0 && isActiveStage && (
                    <button
                      onClick={async () => {
                        if (!confirm('Regenerate current round? It will be deleted and re-generated with the selected model.')) return
                        setRollingBack(true)
                        setError(null)
                        try {
                          await discoverApi.rollback(projectId)
                          await handleGenerateRound()
                        } catch (err) {
                          setError(getErrorMessage(err))
                        } finally {
                          setRollingBack(false)
                        }
                      }}
                      disabled={rollingBack || isGenerating}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 disabled:opacity-50"
                    >
                      {rollingBack ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                      Regenerate
                    </button>
                  )}

                  {/* Generate (purple — primary action) */}
                  {isActiveStage && (
                    <button
                      onClick={handleGenerateRound}
                      disabled={isGenerating}
                      className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50"
                    >
                      {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                      {currentRounds.length === 0 ? 'Start Round 1' : 'Next Round'}
                    </button>
                  )}

                  {/* Advance to Video (green — forward) */}
                  {project.stage === 'images' && imageFinalistId && !isGenerating && (
                    <button
                      onClick={() => doAdvanceToVideo(imageFinalistId)}
                      disabled={advancing}
                      className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                      {advancing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                      Advance to Video
                    </button>
                  )}

                  {/* Advance to Audio (green — forward) */}
                  {project.stage === 'videos' && videoFinalistId && !isGenerating && (
                    <button
                      onClick={handleAdvanceToAudio}
                      disabled={advancing}
                      className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                      {advancing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                      {advancing ? 'Advancing...' : 'Select Audio'}
                    </button>
                  )}

                  {/* Extraction/Completed */}
                  {(project.stage === 'extraction' || project.stage === 'completed') && (
                    <button
                      onClick={handleCreateAnotherTemplate}
                      disabled={creatingTemplate}
                      className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                      {creatingTemplate ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                      {project.stage === 'completed' ? 'Create New Template' : 'Create Template'}
                    </button>
                  )}
                </div>
              </div>
            </div>
        </div>}

    </div>
  )
}
