/**
 * HookSelector - Select audio hook for ai_music provider
 *
 * Displays:
 * - Video player (muted, from video_url)
 * - Audio previews for each hook
 * - Hook metadata (energy, type, reason, timing)
 * - Synchronized playback
 */
import { useState, useRef, useEffect } from 'react'
import {
  Volume2,
  Play,
  Pause,
  Music,
  CheckCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react'

// Hook data from ai_music provider
export interface HookData {
  start: number
  end: number
  duration: number
  reason: string
  energy: 'low' | 'medium' | 'high'
  type: string // chorus, drop, bridge, intro, verse, outro
}

// Variant from ai_music provider
export interface AiMusicVariant {
  hook: HookData
  preview_url: string
  video_id: number
  index: number
  track_index?: number  // Which track (0 or 1 for Suno)
  track_title?: string  // Track title from Suno
  hook_index?: number   // Hook index within track (0-3)
}

interface HookSelectorProps {
  videoUrl: string // Original video without audio
  variants: AiMusicVariant[]
  selectedIndex: number
  onSelect: (index: number) => void
  onConfirm: () => void
  onRegenerate: (feedback?: string) => void  // Generate new music + hooks
  isLoading: boolean
  isRegenerating?: boolean
  musicPrompt?: string
}


export default function HookSelector({
  videoUrl,
  variants,
  selectedIndex,
  onSelect,
  onConfirm,
  onRegenerate,
  isLoading,
  isRegenerating,
  musicPrompt,
}: HookSelectorProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [feedback, setFeedback] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  const currentVariant = variants[selectedIndex]

  // Sync video and audio playback
  const handlePlayPause = () => {
    if (!videoRef.current || !audioRef.current) return

    if (isPlaying) {
      videoRef.current.pause()
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      // Reset to start
      videoRef.current.currentTime = 0
      audioRef.current.currentTime = 0

      // Play both
      Promise.all([
        videoRef.current.play(),
        audioRef.current.play(),
      ]).then(() => {
        setIsPlaying(true)
      }).catch(() => {
        setIsPlaying(false)
      })
    }
  }

  // Stop when video ends
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleEnded = () => {
      setIsPlaying(false)
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.currentTime = 0
      }
    }

    video.addEventListener('ended', handleEnded)
    return () => video.removeEventListener('ended', handleEnded)
  }, [])

  // Reset playback when variant changes
  useEffect(() => {
    setIsPlaying(false)
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      videoRef.current.pause()
    }
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      audioRef.current.pause()
    }
  }, [selectedIndex])

  return (
    <div className="space-y-4">
      {/* Music prompt info */}
      {musicPrompt && (
        <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
          <div className="flex items-start space-x-2">
            <Music className="h-5 w-5 text-purple-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-purple-700">Generated Music</p>
              <p className="text-sm text-purple-600">{musicPrompt}</p>
            </div>
          </div>
        </div>
      )}

      {/* Video + Audio Preview */}
      <div className="flex justify-center">
        <div className="relative w-full max-w-sm">
          {/* Video (muted) */}
          <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              src={videoUrl}
              muted
              playsInline
              className="w-full h-full object-contain"
            />
          </div>

          {/* Play/Pause overlay */}
          <button
            onClick={handlePlayPause}
            className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition group"
          >
            <div className="w-16 h-16 bg-white/90 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition">
              {isPlaying ? (
                <Pause className="h-8 w-8 text-purple-600" />
              ) : (
                <Play className="h-8 w-8 text-purple-600 ml-1" />
              )}
            </div>
          </button>

          {/* Hidden audio element */}
          {currentVariant && (
            <audio
              ref={audioRef}
              src={currentVariant.preview_url}
              preload="auto"
            />
          )}
        </div>
      </div>

      {/* Hook Grid 2x4 */}
      <div className="space-y-3">
        {/* Group variants by track */}
        {[0, 1].map((trackIdx) => {
          const trackVariants = variants.filter(v => (v.track_index ?? 0) === trackIdx)
          if (trackVariants.length === 0) return null

          const trackTitle = trackVariants[0]?.track_title || `Track ${trackIdx + 1}`

          return (
            <div key={trackIdx} className="space-y-2">
              {/* Track label */}
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                {trackTitle}
              </div>

              {/* Hooks row (4 columns) */}
              <div className="grid grid-cols-4 gap-2">
                {trackVariants.map((variant) => {
                  const isSelected = selectedIndex === variant.index
                  const hookNum = (variant.hook_index ?? variant.index % 4) + 1

                  return (
                    <button
                      key={variant.index}
                      onClick={() => onSelect(variant.index)}
                      className={`p-3 rounded-lg border-2 transition-all ${
                        isSelected
                          ? 'border-purple-500 bg-purple-50 shadow-md'
                          : 'border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50/50'
                      }`}
                    >
                      <div className="flex flex-col items-center space-y-1">
                        <Volume2 className={`h-5 w-5 ${isSelected ? 'text-purple-600' : 'text-gray-400'}`} />
                        <span className={`text-sm font-medium ${isSelected ? 'text-purple-700' : 'text-gray-600'}`}>
                          Hook {hookNum}
                        </span>
                        <span className="text-xs text-gray-400">
                          {variant.hook.type}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Feedback input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Feedback (optional)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Describe what to change..."
          className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 resize-none"
          rows={2}
        />
      </div>

      {/* Action Buttons */}
      <div className="flex space-x-3">
        <button
          onClick={onConfirm}
          disabled={isLoading || isRegenerating}
          className="flex-1 flex items-center justify-center px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          ) : (
            <CheckCircle className="h-5 w-5 mr-2" />
          )}
          {isLoading ? 'Merging audio...' : 'Complete'}
        </button>
        <button
          onClick={() => {
            onRegenerate(feedback || undefined)
            setFeedback('')
          }}
          disabled={isLoading || isRegenerating}
          className="flex items-center justify-center px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
        >
          {isRegenerating ? (
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="h-5 w-5 mr-2" />
          )}
          Regenerate
        </button>
      </div>
    </div>
  )
}
