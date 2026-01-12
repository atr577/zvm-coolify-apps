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
  Zap,
  Clock,
  CheckCircle,
  Loader2,
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
}

interface HookSelectorProps {
  videoUrl: string // Original video without audio
  variants: AiMusicVariant[]
  selectedIndex: number
  onSelect: (index: number) => void
  onConfirm: () => void
  isLoading: boolean
  musicPrompt?: string
}

// Energy badge colors
const ENERGY_COLORS = {
  low: 'bg-blue-100 text-blue-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-700',
}

// Type badge colors
const TYPE_COLORS: Record<string, string> = {
  chorus: 'bg-purple-100 text-purple-700',
  drop: 'bg-pink-100 text-pink-700',
  bridge: 'bg-green-100 text-green-700',
  intro: 'bg-cyan-100 text-cyan-700',
  verse: 'bg-gray-100 text-gray-700',
  outro: 'bg-orange-100 text-orange-700',
}

export default function HookSelector({
  videoUrl,
  variants,
  selectedIndex,
  onSelect,
  onConfirm,
  isLoading,
  musicPrompt,
}: HookSelectorProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  const currentVariant = variants[selectedIndex]
  const currentHook = currentVariant?.hook

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

  // Format time as MM:SS.s
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(1)
    return `${mins}:${secs.padStart(4, '0')}`
  }

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

      {/* Hook Tabs */}
      <div className="flex border-b border-gray-200">
        {variants.map((_, index) => (
          <button
            key={index}
            onClick={() => onSelect(index)}
            className={`flex-1 py-3 px-2 text-sm font-medium transition-colors ${
              selectedIndex === index
                ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Volume2 className="h-4 w-4 inline mr-1" />
            Hook {index + 1}
          </button>
        ))}
      </div>

      {/* Hook Details */}
      {currentHook && (
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          {/* Badges */}
          <div className="flex flex-wrap gap-2">
            <span className={`px-2 py-1 text-xs font-medium rounded ${ENERGY_COLORS[currentHook.energy]}`}>
              <Zap className="h-3 w-3 inline mr-1" />
              {currentHook.energy}
            </span>
            <span className={`px-2 py-1 text-xs font-medium rounded ${TYPE_COLORS[currentHook.type] || 'bg-gray-100 text-gray-700'}`}>
              {currentHook.type}
            </span>
            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700">
              <Clock className="h-3 w-3 inline mr-1" />
              {formatTime(currentHook.start)} - {formatTime(currentHook.end)}
            </span>
          </div>

          {/* Reason */}
          <p className="text-sm text-gray-600">
            <span className="font-medium">Why this hook: </span>
            {currentHook.reason}
          </p>
        </div>
      )}

      {/* Confirm Button */}
      <div className="flex justify-center pt-2">
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50 flex items-center"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Merging audio...
            </>
          ) : (
            <>
              <CheckCircle className="h-5 w-5 mr-2" />
              Select Hook {selectedIndex + 1}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
