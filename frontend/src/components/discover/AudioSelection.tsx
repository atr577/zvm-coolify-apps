import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Play, Pause, Volume2, Loader2, Music, Zap, Library,
  RefreshCw,
} from 'lucide-react'
import { discoverApi, audioLibraryApi } from '@/services/api'
import type { DiscoverProject, DiscoverAudioVariant, AudioHook, AudioLibraryItem } from '@/types'
import { getMediaUrl } from '@/utils/video'

type AudioTab = 'sfx' | 'music' | 'library'

interface AudioSelectionProps {
  project: DiscoverProject
  onRefresh: () => void
  onVariantSelect?: (variantId: number | null) => void
}

export default function AudioSelection({ project, onRefresh, onVariantSelect }: AudioSelectionProps) {
  const [activeTab, setActiveTab] = useState<AudioTab>('sfx')
  const [mode, setMode] = useState<'auto' | 'manual'>('auto')
  const [prompt, setPrompt] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  // Library state
  const [libraryItems, setLibraryItems] = useState<AudioLibraryItem[]>([])
  const [libraryLoading, setLibraryLoading] = useState(false)

  // Selected variant for preview
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null)
  const [selectedHook, setSelectedHook] = useState<AudioHook | null>(null)

  // Refs
  const audioRef = useRef<HTMLAudioElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const timeUpdateRef = useRef<(() => void) | null>(null)
  const fadeRafRef = useRef<number | null>(null)

  const FADE_MS = 500

  const variants = project.audio_variants || []
  const sfxVariants = variants.filter(v => v.audio_type === 'sfx')
  const musicVariants = variants.filter(v => v.audio_type === 'music')
  const libraryVariants = variants.filter(v => v.audio_type === 'library')

  const completedSfx = sfxVariants.filter(v => v.status === 'completed').length
  const completedMusic = musicVariants.filter(v => v.status === 'completed').length
  const isGenerating = variants.some(v => v.status === 'generating')

  const selectedVariant = selectedVariantId
    ? variants.find(v => v.id === selectedVariantId)
    : null

  const currentVariants = activeTab === 'sfx' ? sfxVariants
    : activeTab === 'music' ? musicVariants
    : libraryVariants

  // Get finalist video
  const finalistVideo = (() => {
    for (const round of project.rounds) {
      if (round.round_type === 'video') {
        const item = round.items.find(i => i.id === project.finalist_video_item_id)
        if (item) return item
      }
    }
    return null
  })()
  const finalistVideoUrl = finalistVideo
    ? getMediaUrl(finalistVideo.local_path, finalistVideo.result_url)
    : null

  const audioSrc = selectedVariant?.file_url || undefined

  // Poll for generating variants
  useEffect(() => {
    if (!isGenerating) return
    const interval = setInterval(onRefresh, 3000)
    return () => clearInterval(interval)
  }, [isGenerating, onRefresh])

  // Reset playback when variant changes
  useEffect(() => {
    setIsPlaying(false)
    setSelectedHook(null)
    cleanup()
    if (videoRef.current) { videoRef.current.currentTime = 0; videoRef.current.pause() }
    if (audioRef.current) { audioRef.current.currentTime = 0; audioRef.current.pause() }
  }, [selectedVariantId])

  // Stop audio when video ends
  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    const handleEnded = () => {
      setIsPlaying(false)
      if (audioRef.current) { audioRef.current.pause(); audioRef.current.currentTime = 0 }
    }
    video.addEventListener('ended', handleEnded)
    return () => video.removeEventListener('ended', handleEnded)
  }, [])

  // Auto-select first completed variant
  useEffect(() => {
    if (selectedVariantId) return
    const first = currentVariants.find(v => v.status === 'completed')
    if (first) setSelectedVariantId(first.id)
  }, [currentVariants, selectedVariantId])

  // Notify parent of variant selection changes
  useEffect(() => {
    onVariantSelect?.(selectedVariantId)
  }, [selectedVariantId, onVariantSelect])

  const cleanup = () => {
    if (timeUpdateRef.current && audioRef.current) {
      audioRef.current.removeEventListener('timeupdate', timeUpdateRef.current)
      timeUpdateRef.current = null
    }
    if (fadeRafRef.current) {
      cancelAnimationFrame(fadeRafRef.current)
      fadeRafRef.current = null
    }
    if (audioRef.current) audioRef.current.volume = 1
  }

  const playFromHook = (hook: AudioHook) => {
    const audio = audioRef.current
    const video = videoRef.current
    if (!audio || !video) return

    cleanup()

    const startSec = hook.start_ms / 1000
    const endSec = hook.end_ms / 1000
    const fadeSec = FADE_MS / 1000
    const fadeOutStart = endSec - fadeSec

    video.currentTime = 0
    audio.currentTime = startSec
    audio.volume = 0

    const tick = () => {
      if (!audioRef.current || audioRef.current.paused) return
      const t = audioRef.current.currentTime

      if (t >= endSec) {
        audioRef.current.pause()
        videoRef.current?.pause()
        audioRef.current.volume = 1
        setIsPlaying(false)
        fadeRafRef.current = null
        return
      }

      if (t < startSec + fadeSec) {
        audioRef.current.volume = Math.max(0, Math.min(1, (t - startSec) / fadeSec))
      } else if (t >= fadeOutStart) {
        audioRef.current.volume = Math.max(0, (endSec - t) / fadeSec)
      } else {
        audioRef.current.volume = 1
      }

      fadeRafRef.current = requestAnimationFrame(tick)
    }

    Promise.all([video.play(), audio.play()])
      .then(() => {
        setIsPlaying(true)
        fadeRafRef.current = requestAnimationFrame(tick)
      })
      .catch(() => {
        setIsPlaying(false)
        cleanup()
      })
  }

  const handlePlayPause = () => {
    const video = videoRef.current
    const audio = audioRef.current
    if (!video || !audio) return

    if (isPlaying) {
      video.pause()
      audio.pause()
      setIsPlaying(false)
      cleanup()
    } else if (selectedHook) {
      playFromHook(selectedHook)
    } else {
      // No hook — play full track synced with video
      video.currentTime = 0
      audio.currentTime = 0
      Promise.all([video.play(), audio.play()])
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false))
    }
  }

  const handleGenerate = async () => {
    setError(null)
    setGenerating(true)
    try {
      if (activeTab === 'sfx') {
        await discoverApi.generateSfx(project.id, mode, mode === 'manual' ? prompt : undefined)
      } else {
        await discoverApi.generateMusic(project.id, mode, mode === 'manual' ? prompt : undefined)
      }
      setPrompt('')
      onRefresh()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const handleSelectHook = (variant: DiscoverAudioVariant, hook: AudioHook) => {
    setSelectedHook(hook)
    playFromHook(hook)
    // Record selection on backend (fire-and-forget)
    discoverApi.selectHook(project.id, variant.id, hook.start_ms, hook.end_ms)
      .catch(() => {/* selection recording is best-effort for preview */})
  }

  const loadLibrary = useCallback(async () => {
    setLibraryLoading(true)
    try {
      const videoDurationMs = parseFloat(project.video_duration.replace('s', '')) * 1000
      const res = await audioLibraryApi.search(
        (project as any).workspace_id || 0,
        { min_duration_ms: videoDurationMs }
      )
      setLibraryItems(res.data.items)
    } catch {
      setLibraryItems([])
    } finally {
      setLibraryLoading(false)
    }
  }, [project])

  const handleSelectLibrary = async (libraryItemId: number) => {
    setError(null)
    try {
      await discoverApi.selectLibrary(project.id, libraryItemId)
      onRefresh()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Library selection failed')
    }
  }

  const formatMs = (ms: number) => {
    const s = Math.floor(ms / 1000)
    const m = Math.floor(s / 60)
    return `${m}:${String(s % 60).padStart(2, '0')}`
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>
      )}

      {/* Side-by-side: Video | Controls */}
      <div className="flex gap-6">
        {/* LEFT: Video preview */}
        <div className="flex-shrink-0 w-56">
          <div className="relative sticky top-4">
            {finalistVideoUrl && (
              <div className="aspect-[9/16] bg-black rounded-xl overflow-hidden">
                <video
                  ref={videoRef}
                  src={finalistVideoUrl}
                  muted
                  playsInline
                  preload="metadata"
                  className="w-full h-full object-contain"
                />
              </div>
            )}

            {/* Play/Pause overlay */}
            {selectedVariant && selectedVariant.status === 'completed' && (
              <button
                onClick={handlePlayPause}
                className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition group"
              >
                <div className="w-12 h-12 bg-white/90 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition">
                  {isPlaying ? (
                    <Pause className="h-6 w-6 text-purple-600" />
                  ) : (
                    <Play className="h-6 w-6 text-purple-600 ml-0.5" />
                  )}
                </div>
              </button>
            )}

            {/* Hidden audio element */}
            {audioSrc && <audio ref={audioRef} src={audioSrc} preload="auto" />}
          </div>
        </div>

        {/* RIGHT: Controls */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Tabs */}
          <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
            {([
              { id: 'sfx' as AudioTab, label: 'Sound FX', icon: Zap },
              { id: 'music' as AudioTab, label: 'Music', icon: Music },
              { id: 'library' as AudioTab, label: 'Library', icon: Library },
            ]).map(tab => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id)
                  setSelectedVariantId(null)
                  if (tab.id === 'library') loadLibrary()
                }}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white shadow-sm text-gray-900'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Generate panel (SFX / Music) */}
          {activeTab !== 'library' && (
            <div className="p-3 bg-gray-50 rounded-lg space-y-2">
              <div className="flex items-center gap-2">
                {(['auto', 'manual'] as const).map(m => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                      mode === m
                        ? 'bg-purple-100 text-purple-700 border border-purple-200'
                        : 'bg-white text-gray-500 border border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {m === 'auto' ? 'Auto prompt' : 'Manual prompt'}
                  </button>
                ))}
                <div className="flex-1" />
                <button
                  onClick={handleGenerate}
                  disabled={generating || isGenerating || (mode === 'manual' && !prompt.trim()) ||
                    (activeTab === 'sfx' && completedSfx >= 3) ||
                    (activeTab === 'music' && completedMusic >= 3)
                  }
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 disabled:opacity-50"
                >
                  {generating || isGenerating ? (
                    <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generating...</>
                  ) : (
                    <><RefreshCw className="h-3.5 w-3.5" /> Generate</>
                  )}
                </button>
              </div>

              {mode === 'manual' && (
                <textarea
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder={activeTab === 'sfx'
                    ? 'Describe the sound effects...'
                    : 'Describe the music mood, genre, tempo...'
                  }
                  className="w-full p-2 text-sm border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  rows={2}
                  maxLength={500}
                />
              )}
            </div>
          )}

          {/* Library browser */}
          {activeTab === 'library' && (
            <div className="p-3 bg-gray-50 rounded-lg space-y-2">
              {libraryLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading library...
                </div>
              ) : libraryItems.length === 0 ? (
                <p className="text-sm text-gray-500">No audio in library yet. Generate SFX or Music first.</p>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {libraryItems.map(item => (
                    <div key={item.id} className="flex items-center justify-between p-2 bg-white border border-gray-200 rounded-lg hover:border-purple-300 transition">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded font-medium">
                            {item.source_type}
                          </span>
                          <span className="text-sm truncate">{item.prompt || 'Auto-generated'}</span>
                        </div>
                        <span className="text-xs text-gray-400">{formatMs(item.duration_ms)}</span>
                      </div>
                      <button
                        onClick={() => handleSelectLibrary(item.id)}
                        className="ml-2 px-2 py-1 text-xs font-medium text-purple-600 border border-purple-300 rounded hover:bg-purple-50"
                      >
                        Use
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Generating indicator */}
          {isGenerating && (
            <div className="flex items-center gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
              <Loader2 className="h-4 w-4 animate-spin" /> Generating audio...
            </div>
          )}

          {/* Variant cards */}
          {currentVariants.filter(v => v.status === 'completed').length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {currentVariants.filter(v => v.status === 'completed').map((variant, idx) => {
                const isSelected = selectedVariantId === variant.id
                return (
                  <button
                    key={variant.id}
                    onClick={() => setSelectedVariantId(variant.id)}
                    className={`p-2.5 rounded-lg border-2 transition-all ${
                      isSelected
                        ? 'border-purple-500 bg-purple-50 shadow-md'
                        : 'border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50/50'
                    }`}
                  >
                    <div className="flex flex-col items-center space-y-0.5">
                      <Volume2 className={`h-4 w-4 ${isSelected ? 'text-purple-600' : 'text-gray-400'}`} />
                      <span className={`text-sm font-medium ${isSelected ? 'text-purple-700' : 'text-gray-600'}`}>
                        Variant {idx + 1}
                      </span>
                      <span className="text-xs text-gray-400">
                        {variant.prompt_mode === 'auto' ? 'Auto' : 'Manual'}
                        {variant.duration_ms ? ` · ${formatMs(variant.duration_ms)}` : ''}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          )}

          {/* Prompt display for selected variant */}
          {selectedVariant?.prompt && (
            <div className="bg-purple-50 rounded-lg p-2.5 border border-purple-200">
              <div className="flex items-start space-x-2">
                <Music className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-purple-600 line-clamp-2">{selectedVariant.prompt}</p>
              </div>
            </div>
          )}

          {/* Hook grid */}
          {selectedVariant && selectedVariant.detected_hooks && selectedVariant.detected_hooks.length > 1 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Select Hook</p>
              <div className="grid grid-cols-4 gap-1.5">
                {selectedVariant.detected_hooks.map((hook, i) => {
                  const isHookSelected = selectedHook
                    ? selectedHook.start_ms === hook.start_ms
                    : selectedVariant.hook_start_ms === hook.start_ms
                  return (
                    <button
                      key={i}
                      onClick={() => handleSelectHook(selectedVariant, hook)}
                      className={`p-2 rounded-lg border-2 transition-all ${
                        isHookSelected
                          ? 'border-purple-500 bg-purple-50 shadow-md'
                          : 'border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50/50'
                      }`}
                    >
                      <div className="flex flex-col items-center space-y-0.5">
                        <Volume2 className={`h-3.5 w-3.5 ${isHookSelected ? 'text-purple-600' : 'text-gray-400'}`} />
                        <span className={`text-xs font-medium ${isHookSelected ? 'text-purple-700' : 'text-gray-600'}`}>
                          Hook {i + 1}
                        </span>
                        <span className="text-[10px] text-gray-400">
                          {formatMs(hook.start_ms)}-{formatMs(hook.end_ms)}
                        </span>
                        <span className={`text-[10px] px-1 py-0.5 rounded ${
                          hook.energy === 'high' ? 'bg-red-100 text-red-600' :
                          hook.energy === 'medium' ? 'bg-yellow-100 text-yellow-600' :
                          'bg-green-100 text-green-600'
                        }`}>
                          {hook.energy}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Failed variants */}
          {currentVariants.filter(v => v.status === 'failed').map(variant => (
            <div key={variant.id} className="p-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              Generation failed{variant.error_message ? `: ${variant.error_message}` : ''}
            </div>
          ))}

        </div>
      </div>
    </div>
  )
}
