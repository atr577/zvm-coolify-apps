/**
 * VideoPreview - Shows thumbnail with play button, loads video on click
 *
 * Optimized for:
 * - Fast page load (no video preload)
 * - User intent (loads only when they want to watch)
 */
import { useState } from 'react'
import { Play, ImageOff, Loader2 } from 'lucide-react'

interface VideoPreviewProps {
  videoUrl: string | null
  thumbnailUrl?: string | null
  className?: string
  aspectRatio?: string // e.g., "9/16", "16/9"
}

export default function VideoPreview({
  videoUrl,
  thumbnailUrl,
  className = '',
  aspectRatio = '9/16'
}: VideoPreviewProps) {
  const [showVideo, setShowVideo] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [thumbnailError, setThumbnailError] = useState(false)

  // No video available
  if (!videoUrl) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 rounded border border-gray-200 text-gray-400 ${className}`}
        style={{ aspectRatio }}
      >
        No video
      </div>
    )
  }

  // User clicked play - show actual video
  if (showVideo) {
    return (
      <div className={`relative bg-black rounded overflow-hidden ${className}`} style={{ aspectRatio }}>
        <video
          src={videoUrl}
          controls
          autoPlay
          preload="auto"
          className="w-full h-full object-contain"
          onLoadStart={() => setIsLoading(true)}
          onCanPlay={() => setIsLoading(false)}
        />
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <Loader2 className="w-10 h-10 text-white animate-spin" />
          </div>
        )}
      </div>
    )
  }

  // Show thumbnail with play button
  return (
    <div
      className={`relative cursor-pointer group rounded overflow-hidden border border-gray-200 ${className}`}
      style={{ aspectRatio }}
      onClick={() => setShowVideo(true)}
    >
      {/* Thumbnail */}
      {thumbnailUrl && !thumbnailError ? (
        <img
          src={thumbnailUrl}
          alt="Video preview"
          className="w-full h-full object-cover"
          onError={() => setThumbnailError(true)}
        />
      ) : (
        <div className="w-full h-full bg-gray-200 flex items-center justify-center">
          <ImageOff className="w-12 h-12 text-gray-400" />
        </div>
      )}

      {/* Dark overlay on hover */}
      <div className="absolute inset-0 bg-black/30 group-hover:bg-black/40 transition-colors" />

      {/* Play button */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-16 h-16 bg-white/90 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
          <Play className="w-8 h-8 text-purple-600 ml-1" />
        </div>
      </div>
    </div>
  )
}
