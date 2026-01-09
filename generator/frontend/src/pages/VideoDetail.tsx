import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
  CheckCircle, XCircle, Clock,
  ChevronDown, ChevronRight, ThumbsUp, RotateCcw,
  Play, ExternalLink, Loader2, Volume2, Eye, Heart, MessageCircle, Share2,
  Star, RefreshCw, TrendingUp, Youtube, Instagram, Music2, Edit2
} from 'lucide-react'
import { videosApi, workflowApi, metricsApi, CustomPrompt } from '@/services/api'
import PublishingSettings from '@/components/PublishingSettings'
import PublishingMetaEditor from '@/components/PublishingMetaEditor'
import PromptEditor from '@/components/PromptEditor'
import { VideoHeader } from '@/components/video'
import type { KeyMoment, PlatformAdaptation } from '@/types'

function formatMetricNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

export default function VideoDetail() {
  const { id } = useParams<{ id: string }>()
  const videoId = parseInt(id || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [feedback, setFeedback] = useState('')
  const [showAllSteps, setShowAllSteps] = useState(false)
  const [selectedAudioVariant, setSelectedAudioVariant] = useState<number | null>(null)
  const [expandedStepId, setExpandedStepId] = useState<number | null>(null)
  const [regeneratingStep, setRegeneratingStep] = useState<string | null>(null)
  const [customPrompts, setCustomPrompts] = useState<Record<string, CustomPrompt | null>>({})
  const [editedImagePrompt, setEditedImagePrompt] = useState<{
    main_prompt: string
    negative_prompt: string
    style_suffix: string
  } | null>(null)
  const [editedVideoPrompt, setEditedVideoPrompt] = useState<{
    motion_prompt: string
  } | null>(null)

  // Handle custom prompt changes from PromptEditor
  const handlePromptChange = (stepType: string, customPrompt: CustomPrompt | null) => {
    setCustomPrompts(prev => ({ ...prev, [stepType]: customPrompt }))
  }

  const { data: video, isLoading } = useQuery(
    ['video', videoId],
    () => videosApi.get(videoId).then(res => res.data),
    { refetchInterval: 5000 }
  )

  // Fetch metrics for completed videos
  const { data: metricsSummary, refetch: refetchMetrics } = useQuery(
    ['metrics', videoId],
    () => metricsApi.getSummary(videoId).then(res => res.data),
    {
      enabled: video?.status === 'completed',
      refetchInterval: 60000 // Refresh every minute
    }
  )

  // Set author rating mutation
  const setRatingMutation = useMutation(
    (rating: number) => metricsApi.setRating(videoId, rating),
    { onSuccess: () => refetchMetrics() }
  )

  // Auto-generate mutation
  const autoGenerateMutation = useMutation(
    () => workflowApi.autoGenerateToVideo(videoId),
    {
      onSuccess: () => queryClient.invalidateQueries(['video', videoId]),
      onError: (error) => console.error('Auto-generation failed:', error)
    }
  )

  // Auto-start generation (only for AUTO mode)
  // In MANUAL mode, we show PromptEditor and let user trigger generation
  const hasNoWorkflow = !video?.workflow_steps || video?.workflow_steps.length === 0
  const shouldAutoStart = video?.status === 'pending' && hasNoWorkflow && video?.workflow_mode !== 'MANUAL'

  useEffect(() => {
    if (shouldAutoStart && !autoGenerateMutation.isLoading) {
      autoGenerateMutation.mutate()
    }
  }, [shouldAutoStart])

  // Delete mutation
  const deleteMutation = useMutation(
    () => videosApi.delete(videoId),
    { onSuccess: () => navigate(video?.project_id ? `/?project=${video.project_id}` : '/') }
  )

  // Toggle workflow mode mutation
  const toggleWorkflowModeMutation = useMutation(
    () => videosApi.update(videoId, {
      workflow_mode: video?.workflow_mode === 'MANUAL' ? 'AUTO' : 'MANUAL'
    }),
    { onSuccess: () => queryClient.invalidateQueries(['video', videoId]) }
  )

  // Approve step mutation
  const approveStepMutation = useMutation(
    ({ stepId, approved, feedback, stepType: _stepType }: { stepId: number; approved: boolean; feedback?: string; stepType?: string }) =>
      workflowApi.approveStep(stepId, approved, feedback),
    {
      onSuccess: (data, variables) => {
        setFeedback('')
        queryClient.invalidateQueries(['video', videoId])
        // If backend signals to continue workflow (after image approval), trigger auto-generate
        if (data.data?.continue_workflow) {
          autoGenerateMutation.mutate()
        }
        // If rejected (regenerate), immediately trigger regeneration
        if (!variables.approved && variables.stepType) {
          // Small delay to let backend update complete
          setTimeout(() => {
            handleRegenerateStep(variables.stepType!)
          }, 100)
        }
      }
    }
  )

  // Select audio variant mutation
  const selectAudioMutation = useMutation(
    (variantIndex: number) => workflowApi.selectAudioVariant(videoId, variantIndex),
    {
      onSuccess: () => {
        setSelectedAudioVariant(null)
        queryClient.invalidateQueries(['video', videoId])
      },
      onError: (error) => console.error('Audio selection failed:', error)
    }
  )

  // Regenerate step
  const handleRegenerateStep = async (stepType: string) => {
    console.log('handleRegenerateStep called:', stepType, { video: !!video, regeneratingStep })
    if (!video || regeneratingStep) return
    const getStepContent = (type: string) => video.workflow_steps?.find(s => s.step_type === type)?.content
    const customPrompt = customPrompts[stepType] || undefined

    setRegeneratingStep(stepType)
    try {
      switch (stepType) {
        case 'story': {
          const project = video.project
          await workflowApi.generateStory(videoId, {
            theme: project?.story_template || '',
            duration: project?.duration || 5,
            platforms: project?.platforms || [],
            custom_prompt: customPrompt
          })
          break
        }
        case 'description': {
          const storyData = video.story_data || getStepContent('story')
          if (storyData) await workflowApi.generateDescription(videoId, storyData, customPrompt)
          break
        }
        case 'prompt': {
          const descriptionData = video.description_data || getStepContent('description')
          if (descriptionData) await workflowApi.generatePrompt(videoId, descriptionData, customPrompt)
          break
        }
        case 'image': {
          // Use edited image prompt if available, otherwise use prompt_data or image_prompt (for Remix)
          const originalPromptData = video.prompt_data || getStepContent('prompt')
          const aspectRatio = video.project?.aspect_ratio || '9:16'
          const isRemix = video.project?.project_type === 'remix'
          console.log('Regenerate image:', { originalPromptData: !!originalPromptData, imagePrompt: video.image_prompt?.substring(0, 50), aspectRatio, isRemix })

          // For Remix mode: always refill from template unless user edited the prompt
          if (isRemix && !editedImagePrompt) {
            // Pass empty prompt and refillFromTemplate=true to get fresh template from project
            console.log('Remix mode: refilling from project template')
            await workflowApi.generateImage(videoId, '', aspectRatio, 'std', true)
          } else if (!originalPromptData && video.image_prompt) {
            // Fallback for remix with edited prompt
            const prompt = editedImagePrompt?.main_prompt || video.image_prompt
            console.log('Using image_prompt for Remix:', prompt.substring(0, 50))
            await workflowApi.generateImage(videoId, prompt, aspectRatio)
          } else if (originalPromptData || editedImagePrompt) {
            const promptData = editedImagePrompt ? {
              ...originalPromptData,
              main_prompt: editedImagePrompt.main_prompt,
              negative_prompt: editedImagePrompt.negative_prompt,
              style_suffix: editedImagePrompt.style_suffix
            } : originalPromptData
            if (promptData) await workflowApi.generateImage(videoId, promptData, aspectRatio)
          }
          // Clear edited prompt after generation
          setEditedImagePrompt(null)
          break
        }
        case 'scenario': {
          const imageUrl = video.image_url
          const descriptionData = video.description_data || getStepContent('description')
          if (imageUrl && descriptionData) await workflowApi.generateScenario(videoId, imageUrl, descriptionData, customPrompt)
          break
        }
        case 'video': {
          const imageUrl = video.image_url
          const originalScenarioData = video.scenario_data || getStepContent('scenario')
          // Use edited motion prompt if available
          const scenarioData = editedVideoPrompt ? {
            ...originalScenarioData,
            motion_prompt: editedVideoPrompt.motion_prompt
          } : originalScenarioData
          if (imageUrl && scenarioData) await workflowApi.generateVideo(videoId, imageUrl, scenarioData)
          // Clear edited prompt after generation
          setEditedVideoPrompt(null)
          break
        }
        case 'adaptation': {
          const scenarioData = video.scenario_data || getStepContent('scenario')
          const platforms = video.project?.platforms
          if (scenarioData && platforms) await workflowApi.adaptForPlatforms(videoId, scenarioData, platforms, customPrompt)
          break
        }
        case 'audio': {
          await workflowApi.generateAudio(videoId)
          break
        }
      }
      // Clear custom prompt after generation
      setCustomPrompts(prev => ({ ...prev, [stepType]: null }))
      queryClient.invalidateQueries(['video', videoId])
    } catch (error) {
      console.error('Failed to regenerate step:', error)
    } finally {
      setRegeneratingStep(null)
    }
  }

  if (isLoading || !video) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
      </div>
    )
  }

  // Helper functions
  const getStepLabel = (stepType: string) => {
    const map: Record<string, string> = {
      story: 'Story',
      description: 'Description',
      prompt: 'Image Prompt',
      image: 'Image',
      scenario: 'Scenario',
      video: 'Video',
      audio: 'Audio',
      adaptation: 'Adaptation',
      publishing: 'Publishing'
    }
    return map[stepType] || stepType
  }

  // Render step content in human-readable format
  const renderStepContent = (stepType: string, content: Record<string, any> | null) => {
    if (!content) return <p className="text-gray-500 italic">No content</p>

    // Check if feedback was applied during regeneration
    const feedbackHistory: string[] = content._meta?.feedback_history || []
    const iterationCount = feedbackHistory.length
    const FeedbackBadge = iterationCount > 0 ? (
      <div className="mb-2 group relative">
        <div className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full cursor-help">
          <MessageCircle className="h-3 w-3 mr-1" />
          {iterationCount === 1 ? 'Feedback applied' : `${iterationCount} feedback iterations`}
        </div>
        {/* Tooltip with feedback history */}
        <div className="absolute left-0 top-full mt-1 hidden group-hover:block z-10 w-64 p-2 bg-gray-800 text-white text-xs rounded shadow-lg">
          {feedbackHistory.map((fb, i) => (
            <div key={i} className={i > 0 ? 'mt-1 pt-1 border-t border-gray-600' : ''}>
              <span className="text-blue-300">#{i + 1}:</span> {fb}
            </div>
          ))}
        </div>
      </div>
    ) : null

    try {
      switch (stepType.toLowerCase()) {
        case 'story':
          return (
            <div className="space-y-2">
              {FeedbackBadge}
              {content.concept && <div><span className="font-medium">Concept:</span> {content.concept}</div>}
              {content.hook && <div><span className="font-medium">Hook:</span> {content.hook} <span className="text-gray-500">({content.hook_type})</span></div>}
              {content.climax && <div><span className="font-medium">Climax:</span> {content.climax}</div>}
              {content.tone && <div><span className="font-medium">Tone:</span> {content.tone}</div>}
              {content.pacing && <div><span className="font-medium">Pacing:</span> {content.pacing}</div>}
              {content.emotional_trigger && <div><span className="font-medium">Emotion:</span> {content.emotional_trigger}</div>}
              {content.duration && <div><span className="font-medium">Duration:</span> {content.duration}s</div>}
            </div>
          )
        case 'description':
          return (
            <div className="space-y-2">
              {FeedbackBadge}
              {content.scene_summary && <div><span className="font-medium">Scene:</span> {content.scene_summary}</div>}
              {content.main_subject?.description && <div><span className="font-medium">Main Subject:</span> {content.main_subject.description}</div>}
              {content.environment && (
                <div>
                  <span className="font-medium">Environment:</span>
                  <span className="text-sm ml-1">
                    {[content.environment.location, content.environment.time_of_day, content.environment.weather].filter(Boolean).join(', ')}
                  </span>
                </div>
              )}
              {content.visual_style && (
                <div>
                  <span className="font-medium">Style:</span>
                  <span className="text-sm ml-1">
                    {typeof content.visual_style === 'string'
                      ? content.visual_style
                      : [content.visual_style.mood, content.visual_style.lighting, content.visual_style.aesthetic].filter(Boolean).join(', ')}
                  </span>
                </div>
              )}
              {content.key_details && Array.isArray(content.key_details) && (
                <div><span className="font-medium">Details:</span> {content.key_details.join(', ')}</div>
              )}
            </div>
          )
        case 'prompt':
          return (
            <div className="space-y-2">
              {FeedbackBadge}
              {content.main_prompt && <div><span className="font-medium">Prompt:</span> <span className="text-sm">{content.main_prompt}</span></div>}
              {content.negative_prompt && <div><span className="font-medium">Negative:</span> <span className="text-sm text-gray-600">{content.negative_prompt}</span></div>}
              {content.style_keywords && <div><span className="font-medium">Style:</span> {Array.isArray(content.style_keywords) ? content.style_keywords.join(', ') : content.style_keywords}</div>}
            </div>
          )
        case 'image':
          return (
            <div className="space-y-2">
              {content.image_url && (
                <img
                  src={content.image_url}
                  alt="Generated"
                  className="w-full max-w-md rounded-lg shadow-lg"
                  style={{ maxHeight: '400px', objectFit: 'contain' }}
                />
              )}
            </div>
          )
        case 'scenario':
          return (
            <div className="space-y-2">
              {FeedbackBadge}
              {content.motion_prompt && <div><span className="font-medium">Motion:</span> <span className="text-sm">{content.motion_prompt}</span></div>}
              {content.camera_movement && (
                <div>
                  <span className="font-medium">Camera:</span>{' '}
                  {typeof content.camera_movement === 'object'
                    ? `${content.camera_movement.type} (${content.camera_movement.speed}) - ${content.camera_movement.description}`
                    : content.camera_movement}
                </div>
              )}
              {content.subject_action && <div><span className="font-medium">Action:</span> {content.subject_action}</div>}
              {content.key_moments && Array.isArray(content.key_moments) && (
                <div>
                  <span className="font-medium">Key Moments:</span>
                  <ul className="list-disc list-inside ml-2 text-sm">
                    {content.key_moments.map((m: KeyMoment, i: number) => (
                      <li key={i}>{m.timestamp}: {m.action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        case 'video':
          return (
            <div className="space-y-2">
              {content.video_url && (
                <video
                  src={content.video_url}
                  controls
                  className="w-full max-w-md rounded-lg shadow-lg"
                  style={{ maxHeight: '400px' }}
                />
              )}
              {content.task_id && (
                <div className="text-xs text-gray-400">Task ID: {content.task_id}</div>
              )}
            </div>
          )
        case 'adaptation':
          return (
            <div className="space-y-2">
              {FeedbackBadge}
              {Object.entries(content)
                .filter(([key]) => key !== '_meta')
                .map(([platform, data]: [string, PlatformAdaptation | undefined]) => (
                  <div key={platform} className="border-l-2 border-purple-300 pl-3">
                    <div className="font-medium capitalize">{platform}</div>
                    {data?.title && <div className="text-sm"><span className="text-gray-500">Title:</span> {data.title}</div>}
                    {data?.description && <div className="text-sm"><span className="text-gray-500">Description:</span> {data.description}</div>}
                    {data?.hashtags && <div className="text-sm"><span className="text-gray-500">Hashtags:</span> {data.hashtags}</div>}
                  </div>
                ))}
            </div>
          )
        default:
          return (
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(content, null, 2)}
            </pre>
          )
      }
    } catch (e) {
      // Fallback to JSON if rendering fails
      return (
        <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
          {JSON.stringify(content, null, 2)}
        </pre>
      )
    }
  }

  const getStatusIcon = (status: string, size = 5) => {
    const cls = `h-${size} w-${size}`
    switch (status) {
      case 'approved':
      case 'completed':
        return <CheckCircle className={`${cls} text-green-500`} />
      case 'failed':
      case 'rejected':
        return <XCircle className={`${cls} text-red-500`} />
      case 'in_progress':
        return <Loader2 className={`${cls} text-yellow-500 animate-spin`} />
      case 'awaiting_approval':
        return <Clock className={`${cls} text-blue-500`} />
      default:
        return <div className={`${cls} rounded-full border-2 border-gray-300`} />
    }
  }

  // Current step data
  const steps = video.workflow_steps || []
  const currentStep = steps.find(s => {
    const st = s.status?.toLowerCase()
    return st === 'awaiting_approval' || st === 'in_progress'
  })
  const pendingSteps = steps.filter(s => s.status?.toLowerCase() === 'pending')
  // Only show failed step if there's no pending step of the same type (pending supersedes failed)
  const failedStep = steps.find(s => {
    if (s.status?.toLowerCase() !== 'failed') return false
    const hasPendingOfSameType = pendingSteps.some(p => p.step_type === s.step_type)
    return !hasPendingOfSameType
  })
  const completedSteps = steps.filter(s => {
    const st = s.status?.toLowerCase()
    return st === 'approved' || st === 'completed'
  })
  // Remix: Image → Video → Audio (3 steps)
  // Discover: Story → Description → Prompt → Image → Scenario → Video → Audio → Adaptation → Publishing (9 steps)
  const isRemix = video.project?.project_type === 'remix'
  const totalSteps = isRemix ? 3 : 9
  const completedCount = completedSteps.length
  const isCompleted = video.status?.toLowerCase() === 'completed'
  const isPublishing = video.current_step?.toLowerCase() === 'publishing'

  return (
    <div className="max-w-4xl mx-auto">
      <VideoHeader
        title={video.title}
        completedCount={completedCount}
        totalSteps={totalSteps}
        isCompleted={isCompleted}
        workflowMode={video.workflow_mode}
        isRemix={isRemix}
        onToggleMode={() => toggleWorkflowModeMutation.mutate()}
        onDelete={() => confirm('Delete video?') && deleteMutation.mutate()}
      />

      {/* COMPLETED STATE */}
      {isCompleted && (
        <div className="space-y-6">
          {/* Video + Publishing Status */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="grid md:grid-cols-2 gap-6 p-6">
              {/* Video Preview */}
              <div>
                {(video.video_with_audio_url || video.video_url) && (
                  <div className="relative aspect-[9/16] bg-black rounded-lg overflow-hidden">
                    <video
                      src={video.video_with_audio_url ?? video.video_url ?? undefined}
                      controls
                      className="w-full h-full object-contain"
                    />
                    {video.video_with_audio_url && video.video_with_audio_url !== video.video_url && (
                      <div className="absolute bottom-2 left-2">
                        <span className="px-2 py-1 bg-green-500 text-white text-xs rounded flex items-center">
                          <Volume2 className="h-3 w-3 mr-1" />
                          With Audio
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Publishing Metadata & Settings */}
              <div className="flex flex-col">
                {/* Meta Editor */}
                <PublishingMetaEditor
                  videoId={videoId}
                  platforms={video.project?.platforms || []}
                  initialMeta={video.publishing_meta || video.adaptation_data || null}
                />

                {/* Publishing */}
                <div className="mt-4">
                  <PublishingSettings
                    videoId={videoId}
                    publishingStepId={0}
                    adaptationData={video.publishing_meta || video.adaptation_data || {}}
                    platforms={video.project?.platforms || []}
                    videoUrl={video.video_with_audio_url || video.video_url || ''}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Metrics Section */}
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <TrendingUp className="h-5 w-5 mr-2 text-purple-600" />
                Performance Metrics
              </h3>
              <button
                onClick={() => refetchMetrics()}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
                title="Refresh metrics"
              >
                <RefreshCw className="h-4 w-4 text-gray-500" />
              </button>
            </div>

            {/* Author Rating */}
            <div className="mb-6 p-4 bg-purple-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-purple-900">Your Rating (before publish)</span>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setRatingMutation.mutate(star)}
                      className={`p-1 transition ${
                        (metricsSummary?.author_rating || video.author_rating || 0) >= star
                          ? 'text-yellow-400'
                          : 'text-gray-300 hover:text-yellow-300'
                      }`}
                    >
                      <Star className="h-5 w-5 fill-current" />
                    </button>
                  ))}
                </div>
              </div>
              {(metricsSummary?.author_rating || video.author_rating) && (
                <p className="text-xs text-purple-700 mt-1">
                  Rated {metricsSummary?.author_rating || video.author_rating}/5 potential
                </p>
              )}
            </div>

            {/* Totals */}
            {metricsSummary && (metricsSummary.total_views > 0 || metricsSummary.total_likes > 0) ? (
              <>
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <Eye className="h-6 w-6 mx-auto mb-2 text-blue-500" />
                    <div className="text-2xl font-bold text-gray-900">
                      {formatMetricNumber(metricsSummary.total_views)}
                    </div>
                    <div className="text-xs text-gray-500">Views</div>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <Heart className="h-6 w-6 mx-auto mb-2 text-red-500" />
                    <div className="text-2xl font-bold text-gray-900">
                      {formatMetricNumber(metricsSummary.total_likes)}
                    </div>
                    <div className="text-xs text-gray-500">Likes</div>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <MessageCircle className="h-6 w-6 mx-auto mb-2 text-green-500" />
                    <div className="text-2xl font-bold text-gray-900">
                      {formatMetricNumber(metricsSummary.total_comments)}
                    </div>
                    <div className="text-xs text-gray-500">Comments</div>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <Share2 className="h-6 w-6 mx-auto mb-2 text-purple-500" />
                    <div className="text-2xl font-bold text-gray-900">
                      {formatMetricNumber(metricsSummary.total_shares)}
                    </div>
                    <div className="text-xs text-gray-500">Shares</div>
                  </div>
                </div>

                {/* Engagement Rate */}
                {metricsSummary.avg_engagement_rate && (
                  <div className="mb-6 p-4 bg-green-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-green-900">Engagement Rate</span>
                      <span className="text-xl font-bold text-green-700">
                        {metricsSummary.avg_engagement_rate.toFixed(2)}%
                      </span>
                    </div>
                  </div>
                )}

                {/* Per Period Table */}
                {Object.keys(metricsSummary.platforms).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">By Period</h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-gray-500 border-b">
                            <th className="pb-2 w-20">Period</th>
                            <th className="pb-2">Views</th>
                            <th className="pb-2">Likes</th>
                            <th className="pb-2">Comments</th>
                            <th className="pb-2">Shares</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(['30m', '6h', '24h', '7d'] as const).map(period => {
                            // Collect metrics for this period from all platforms
                            const platformMetrics: { platform: string; views: number; likes: number; comments: number; shares: number }[] = []
                            Object.entries(metricsSummary.platforms).forEach(([platformName, periods]) => {
                              if (periods[period]) {
                                const m = periods[period]
                                platformMetrics.push({ platform: platformName, views: m.views, likes: m.likes, comments: m.comments, shares: m.shares })
                              }
                            })
                            if (platformMetrics.length === 0) return null

                            const PlatformIcon = ({ platform }: { platform: string }) => {
                              if (platform === 'youtube') return <Youtube className="h-4 w-4 text-red-600 mr-1" />
                              if (platform === 'instagram') return <Instagram className="h-4 w-4 text-pink-600 mr-1" />
                              if (platform === 'tiktok') return <Music2 className="h-4 w-4 text-black mr-1" />
                              return <span className="text-gray-600 mr-1">•</span>
                            }

                            return (
                              <tr key={period} className="border-b last:border-0">
                                <td className="py-3 font-medium text-gray-700">{period}</td>
                                <td className="py-3">
                                  <div className="flex flex-col gap-1">
                                    {platformMetrics.map(m => (
                                      <span key={m.platform} className="flex items-center">
                                        <PlatformIcon platform={m.platform} />
                                        <span>{m.views.toLocaleString()}</span>
                                      </span>
                                    ))}
                                  </div>
                                </td>
                                <td className="py-3">
                                  <div className="flex flex-col gap-1">
                                    {platformMetrics.map(m => (
                                      <span key={m.platform} className="flex items-center">
                                        <PlatformIcon platform={m.platform} />
                                        <span>{m.likes.toLocaleString()}</span>
                                      </span>
                                    ))}
                                  </div>
                                </td>
                                <td className="py-3">
                                  <div className="flex flex-col gap-1">
                                    {platformMetrics.map(m => (
                                      <span key={m.platform} className="flex items-center">
                                        <PlatformIcon platform={m.platform} />
                                        <span>{m.comments.toLocaleString()}</span>
                                      </span>
                                    ))}
                                  </div>
                                </td>
                                <td className="py-3">
                                  <div className="flex flex-col gap-1">
                                    {platformMetrics.map(m => (
                                      <span key={m.platform} className="flex items-center">
                                        <PlatformIcon platform={m.platform} />
                                        <span>{m.shares.toLocaleString()}</span>
                                      </span>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <TrendingUp className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>No metrics yet</p>
                <p className="text-sm mt-1">Metrics will be collected automatically after publishing</p>
              </div>
            )}
          </div>

          {/* Collapsed Steps */}
          <div className="bg-white rounded-xl shadow-sm border">
            <button
              onClick={() => setShowAllSteps(!showAllSteps)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
            >
              <span className="font-medium text-gray-700">
                All steps ({completedCount}/{totalSteps} completed)
              </span>
              {showAllSteps ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
            </button>

            {showAllSteps && (
              <div className="border-t">
                {steps.map((step, index) => (
                  <div key={step.id} className="border-b last:border-0">
                    <button
                      onClick={() => setExpandedStepId(expandedStepId === step.id ? null : step.id)}
                      className={`w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 transition ${
                        expandedStepId === step.id ? 'bg-gray-50' : ''
                      }`}
                    >
                      {getStatusIcon(step.status)}
                      <span className="text-sm text-gray-500 w-16">Step {index + 1}</span>
                      <span className="text-sm font-medium text-gray-700">{getStepLabel(step.step_type)}</span>
                      <span className="text-xs text-gray-400 capitalize ml-auto mr-2">
                        {step.status?.toLowerCase().replace('_', ' ')}
                      </span>
                      {step.content && (
                        expandedStepId === step.id
                          ? <ChevronDown className="h-4 w-4 text-gray-400" />
                          : <ChevronRight className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                    {expandedStepId === step.id && step.content && (
                      <div className="px-4 pb-4 pt-2 bg-gray-50 border-t">
                        <div className="text-sm text-gray-700">
                          {renderStepContent(step.step_type, step.content)}
                        </div>
                        {step.generation_time_seconds && (
                          <div className="mt-2 text-xs text-gray-400">
                            Generated in {step.generation_time_seconds.toFixed(1)}s
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* IN PROGRESS STATE */}
      {!isCompleted && (
        <div className="space-y-6">
          {/* First step - Story generation for new MANUAL videos */}
          {video.workflow_mode === 'MANUAL' && steps.length === 0 && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
                <div className="flex items-center space-x-3">
                  <Play className="h-6 w-6 text-purple-600" />
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">Step 1: Story</h2>
                    <p className="text-sm text-gray-600">Generate the story concept</p>
                  </div>
                </div>
              </div>
              <div className="p-6 space-y-4">
                {/* PromptEditor for Story */}
                <PromptEditor
                  videoId={videoId}
                  stepType="story"
                  context={{
                    theme: video.project?.story_template,
                    duration: video.project?.duration,
                    platforms: video.project?.platforms
                  }}
                  onPromptChange={(customPrompt) => handlePromptChange('story', customPrompt)}
                  disabled={!!regeneratingStep}
                />

                <button
                  onClick={() => handleRegenerateStep('story')}
                  disabled={!!regeneratingStep}
                  className="w-full flex items-center justify-center px-6 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
                >
                  {regeneratingStep === 'story' ? (
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Play className="h-5 w-5 mr-2" />
                  )}
                  {regeneratingStep === 'story' ? 'Generating...' : 'Generate Story'}
                  {customPrompts['story'] && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
                      <Edit2 className="h-3 w-3 mr-1" />
                      Custom
                    </span>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Publishing Settings */}
          {isPublishing && video.adaptation_data && (
            <PublishingSettings
              videoId={videoId}
              publishingStepId={steps.find(s => s.step_type === 'publishing')?.id || 0}
              adaptationData={video.adaptation_data}
              platforms={video.project?.platforms || []}
              videoUrl={video.video_with_audio_url || video.video_url || ''}
            />
          )}

          {/* Current Step Card */}
          {currentStep && !isPublishing && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
              {/* Step Header */}
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(currentStep.status, 6)}
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">
                        Step {steps.indexOf(currentStep) + 1}: {getStepLabel(currentStep.step_type)}
                      </h2>
                      <p className="text-sm text-gray-600 capitalize">
                        {currentStep.status.replace('_', ' ')}
                      </p>
                    </div>
                  </div>
                  {currentStep.generation_time_seconds && (
                    <span className="text-sm text-gray-500">
                      {currentStep.generation_time_seconds.toFixed(1)}s
                    </span>
                  )}
                </div>
              </div>

              {/* Step Content */}
              <div className="p-6">
                {/* Preview for image/video steps */}
                {currentStep.step_type === 'image' && currentStep.content?.image_url && (
                  <div className="mb-6">
                    <img
                      src={currentStep.content.image_url}
                      alt="Preview"
                      className="max-h-96 mx-auto rounded-lg shadow"
                    />
                  </div>
                )}
                {currentStep.step_type === 'video' && currentStep.content?.video_url && (
                  <div className="mb-6">
                    <video
                      src={currentStep.content.video_url}
                      controls
                      className="max-h-96 mx-auto rounded-lg shadow"
                    />
                  </div>
                )}

                {/* Audio variants selection - Tabs UI */}
                {currentStep.step_type === 'audio' && video.audio_variants && video.audio_variants.length > 0 && (
                  <div className="mb-6">
                    {/* Tabs */}
                    <div className="flex border-b border-gray-200 mb-4">
                      {video.audio_variants.map((_: string, index: number) => (
                        <button
                          key={index}
                          onClick={() => setSelectedAudioVariant(index)}
                          className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                            (selectedAudioVariant ?? 0) === index
                              ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          <Volume2 className="h-4 w-4 inline mr-1" />
                          Вариант {index + 1}
                        </button>
                      ))}
                    </div>

                    {/* Video Player */}
                    <div className="flex justify-center mb-4">
                      <div className="w-full max-w-sm">
                        <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
                          <video
                            key={selectedAudioVariant ?? 0}
                            src={video.audio_variants[selectedAudioVariant ?? 0]}
                            controls
                            autoPlay
                            className="w-full h-full object-contain"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Select Button */}
                    <div className="flex justify-center">
                      <button
                        onClick={() => selectAudioMutation.mutate(selectedAudioVariant ?? 0)}
                        disabled={selectAudioMutation.isLoading}
                        className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50 flex items-center"
                      >
                        {selectAudioMutation.isLoading ? (
                          <>
                            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                            Сохранение...
                          </>
                        ) : (
                          <>
                            <CheckCircle className="h-5 w-5 mr-2" />
                            Выбрать вариант {(selectedAudioVariant ?? 0) + 1}
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Text content for other steps - human readable */}
                {currentStep.content && currentStep.step_type !== 'image' && currentStep.step_type !== 'video' && currentStep.step_type !== 'audio' && (
                  <div className="mb-6 bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                    <div className="text-sm text-gray-700">
                      {renderStepContent(currentStep.step_type, currentStep.content)}
                    </div>
                  </div>
                )}

                {/* Loading state */}
                {currentStep.status === 'in_progress' && (
                  <div className="flex flex-col items-center py-8">
                    <Loader2 className="h-12 w-12 animate-spin text-purple-600 mb-4" />
                    <p className="text-gray-600">Generating...</p>
                  </div>
                )}

                {/* Approve/Reject controls (not for audio - handled by variant selection) */}
                {currentStep.status === 'awaiting_approval' && currentStep.step_type !== 'audio' && (
                  <div className="space-y-4">
                    <textarea
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                      rows={2}
                      placeholder="Feedback (optional)..."
                    />
                    <div className="flex space-x-3">
                      <button
                        onClick={() => approveStepMutation.mutate({
                          stepId: currentStep.id,
                          approved: true,
                          feedback
                        })}
                        disabled={approveStepMutation.isLoading}
                        className="flex-1 flex items-center justify-center px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                      >
                        <ThumbsUp className="h-5 w-5 mr-2" />
                        Approve
                      </button>
                      <button
                        onClick={() => approveStepMutation.mutate({
                          stepId: currentStep.id,
                          approved: false,
                          feedback,
                          stepType: currentStep.step_type
                        })}
                        disabled={approveStepMutation.isLoading || !!regeneratingStep}
                        className="flex-1 flex items-center justify-center px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
                      >
                        <RotateCcw className="h-5 w-5 mr-2" />
                        {regeneratingStep === currentStep.step_type ? 'Regenerating...' : 'Regenerate'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Failed step - show error and regenerate button */}
          {failedStep && !currentStep && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-red-200 overflow-hidden">
              <div className="bg-red-50 p-4 border-b">
                <div className="flex items-center space-x-3">
                  <XCircle className="h-6 w-6 text-red-500" />
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">
                      Step {steps.indexOf(failedStep) + 1}: {getStepLabel(failedStep.step_type)}
                    </h2>
                    <p className="text-sm text-red-600">Failed - click to regenerate</p>
                  </div>
                </div>
              </div>
              <div className="p-6 space-y-4">
                {failedStep.content && (
                  <div className="bg-gray-50 rounded-lg p-4 max-h-40 overflow-y-auto">
                    <div className="text-sm text-gray-600">
                      {renderStepContent(failedStep.step_type, failedStep.content)}
                    </div>
                  </div>
                )}

                {/* PromptEditor for AI-generated steps */}
                {['story', 'description', 'prompt', 'scenario', 'adaptation'].includes(failedStep.step_type) && (
                  <PromptEditor
                    videoId={videoId}
                    stepType={failedStep.step_type as 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'}
                    context={
                      failedStep.step_type === 'description' ? { story_data: video.story_data } :
                      failedStep.step_type === 'prompt' ? { description_data: video.description_data } :
                      failedStep.step_type === 'scenario' ? { image_url: video.image_url, description_data: video.description_data } :
                      failedStep.step_type === 'adaptation' ? { scenario_data: video.scenario_data, platforms: video.project?.platforms } :
                      undefined
                    }
                    onPromptChange={(customPrompt) => handlePromptChange(failedStep.step_type, customPrompt)}
                    disabled={!!regeneratingStep}
                  />
                )}

                <button
                  onClick={() => handleRegenerateStep(failedStep.step_type)}
                  disabled={!!regeneratingStep}
                  className="w-full flex items-center justify-center px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition disabled:opacity-50"
                >
                  {regeneratingStep === failedStep.step_type ? (
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <RotateCcw className="h-5 w-5 mr-2" />
                  )}
                  {regeneratingStep === failedStep.step_type ? 'Regenerating...' : `Regenerate ${getStepLabel(failedStep.step_type)}`}
                  {customPrompts[failedStep.step_type] && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
                      <Edit2 className="h-3 w-3 mr-1" />
                      Custom
                    </span>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* No current step but has pending */}
          {!currentStep && !failedStep && pendingSteps.length > 0 && !isPublishing && (
            <div className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">Next: {getStepLabel(pendingSteps[0].step_type)}</h3>
                  <p className="text-sm text-gray-500">
                    {regeneratingStep === pendingSteps[0].step_type ? 'Generating...' : 'Ready to generate'}
                  </p>
                </div>
              </div>

              {/* PromptEditor for AI-generated steps */}
              {['story', 'description', 'prompt', 'scenario', 'adaptation'].includes(pendingSteps[0].step_type) && (
                <PromptEditor
                  videoId={videoId}
                  stepType={pendingSteps[0].step_type as 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'}
                  context={
                    pendingSteps[0].step_type === 'description' ? { story_data: video.story_data } :
                    pendingSteps[0].step_type === 'prompt' ? { description_data: video.description_data } :
                    pendingSteps[0].step_type === 'scenario' ? { image_url: video.image_url, description_data: video.description_data } :
                    pendingSteps[0].step_type === 'adaptation' ? { scenario_data: video.scenario_data, platforms: video.project?.platforms } :
                    undefined
                  }
                  onPromptChange={(customPrompt) => handlePromptChange(pendingSteps[0].step_type, customPrompt)}
                  disabled={!!regeneratingStep}
                />
              )}

              {/* Show editable image prompt for IMAGE step (from previous PROMPT step) */}
              {pendingSteps[0].step_type === 'image' && video.prompt_data && (
                <div className="border rounded-lg bg-gray-50">
                  <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
                    <span className="text-sm font-medium text-gray-700">
                      Image Prompt for KLING
                    </span>
                    {editedImagePrompt && (
                      <div className="flex items-center space-x-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                          <Edit2 className="h-3 w-3 mr-1" />
                          Modified
                        </span>
                        <button
                          onClick={() => setEditedImagePrompt(null)}
                          className="text-xs text-gray-500 hover:text-gray-700"
                        >
                          <RotateCcw className="h-3 w-3" />
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="p-3 space-y-3">
                    <div>
                      <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
                        Main Prompt
                      </label>
                      <textarea
                        value={editedImagePrompt?.main_prompt ?? video.prompt_data.main_prompt ?? ''}
                        onChange={(e) => setEditedImagePrompt(prev => ({
                          main_prompt: e.target.value,
                          negative_prompt: prev?.negative_prompt ?? video.prompt_data?.negative_prompt ?? '',
                          style_suffix: prev?.style_suffix ?? video.prompt_data?.style_suffix ?? ''
                        }))}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                        rows={5}
                        disabled={!!regeneratingStep}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
                        Negative Prompt
                      </label>
                      <textarea
                        value={editedImagePrompt?.negative_prompt ?? video.prompt_data.negative_prompt ?? ''}
                        onChange={(e) => setEditedImagePrompt(prev => ({
                          main_prompt: prev?.main_prompt ?? video.prompt_data?.main_prompt ?? '',
                          negative_prompt: e.target.value,
                          style_suffix: prev?.style_suffix ?? video.prompt_data?.style_suffix ?? ''
                        }))}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-red-700"
                        rows={2}
                        disabled={!!regeneratingStep}
                        placeholder="e.g. blurry, low quality, watermark..."
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
                        Style Suffix
                      </label>
                      <textarea
                        value={editedImagePrompt?.style_suffix ?? video.prompt_data.style_suffix ?? ''}
                        onChange={(e) => setEditedImagePrompt(prev => ({
                          main_prompt: prev?.main_prompt ?? video.prompt_data?.main_prompt ?? '',
                          negative_prompt: prev?.negative_prompt ?? video.prompt_data?.negative_prompt ?? '',
                          style_suffix: e.target.value
                        }))}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                        rows={2}
                        disabled={!!regeneratingStep}
                        placeholder="e.g. cinematic, 8k, professional lighting..."
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Show editable scenario prompt for VIDEO step */}
              {pendingSteps[0].step_type === 'video' && video.scenario_data && (
                <div className="border rounded-lg bg-gray-50">
                  <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
                    <span className="text-sm font-medium text-gray-700">
                      Video Motion Prompt for KLING
                    </span>
                    {editedVideoPrompt && (
                      <div className="flex items-center space-x-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                          <Edit2 className="h-3 w-3 mr-1" />
                          Modified
                        </span>
                        <button
                          onClick={() => setEditedVideoPrompt(null)}
                          className="text-xs text-gray-500 hover:text-gray-700"
                        >
                          <RotateCcw className="h-3 w-3" />
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="p-3 space-y-3">
                    <div>
                      <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
                        Motion Prompt
                      </label>
                      <textarea
                        value={editedVideoPrompt?.motion_prompt ?? video.scenario_data.motion_prompt ?? ''}
                        onChange={(e) => setEditedVideoPrompt({ motion_prompt: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                        rows={4}
                        disabled={!!regeneratingStep}
                      />
                    </div>
                    {video.scenario_data.camera_movement && (
                      <div>
                        <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
                          Camera Movement (info)
                        </label>
                        <pre className="text-xs bg-white p-3 rounded border overflow-x-auto whitespace-pre-wrap text-gray-500">
                          {typeof video.scenario_data.camera_movement === 'object'
                            ? JSON.stringify(video.scenario_data.camera_movement, null, 2)
                            : video.scenario_data.camera_movement}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <button
                onClick={() => handleRegenerateStep(pendingSteps[0].step_type)}
                disabled={!!regeneratingStep}
                className="w-full flex items-center justify-center px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {regeneratingStep === pendingSteps[0].step_type ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                {regeneratingStep === pendingSteps[0].step_type ? 'Generating...' : 'Generate'}
                {(customPrompts[pendingSteps[0].step_type] ||
                  (pendingSteps[0].step_type === 'image' && editedImagePrompt) ||
                  (pendingSteps[0].step_type === 'video' && editedVideoPrompt)) && (
                  <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
                    <Edit2 className="h-3 w-3 mr-1" />
                    Custom Prompt
                  </span>
                )}
              </button>
            </div>
          )}

          {/* Steps Progress */}
          <div className="bg-white rounded-xl shadow-sm border">
            <button
              onClick={() => setShowAllSteps(!showAllSteps)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
            >
              <div className="flex items-center space-x-3">
                <span className="font-medium text-gray-700">
                  Completed steps ({completedCount})
                </span>
                {/* Progress dots */}
                <div className="flex items-center space-x-1">
                  {Array.from({ length: totalSteps }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-2 h-2 rounded-full ${
                        i < completedCount ? 'bg-green-500' :
                        i === completedCount ? 'bg-purple-500' : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
              </div>
              {showAllSteps ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
            </button>

            {showAllSteps && (
              <div className="border-t">
                {steps.map((step, index) => (
                  <div key={step.id} className="border-b last:border-0">
                    <button
                      onClick={() => setExpandedStepId(expandedStepId === step.id ? null : step.id)}
                      className={`w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 transition ${
                        step.id === currentStep?.id ? 'bg-purple-50' : ''
                      } ${expandedStepId === step.id ? 'bg-gray-50' : ''}`}
                    >
                      {getStatusIcon(step.status)}
                      <span className="text-sm text-gray-500 w-16">Step {index + 1}</span>
                      <span className={`text-sm font-medium ${
                        step.id === currentStep?.id ? 'text-purple-700' : 'text-gray-700'
                      }`}>
                        {getStepLabel(step.step_type)}
                      </span>
                      <span className="text-xs text-gray-400 capitalize ml-auto mr-2">
                        {step.status.replace('_', ' ')}
                      </span>
                      {step.content && (
                        expandedStepId === step.id
                          ? <ChevronDown className="h-4 w-4 text-gray-400" />
                          : <ChevronRight className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                    {expandedStepId === step.id && step.content && (
                      <div className="px-4 pb-4 pt-2 bg-gray-50 border-t">
                        <div className="text-sm text-gray-700">
                          {renderStepContent(step.step_type, step.content)}
                        </div>
                        {step.generation_time_seconds && (
                          <div className="mt-2 text-xs text-gray-400">
                            Generated in {step.generation_time_seconds.toFixed(1)}s
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
