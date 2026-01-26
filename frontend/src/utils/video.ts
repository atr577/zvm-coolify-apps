export function formatMetricNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

export function getStepLabel(stepType: string): string {
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

// API base URL for local files
const API_URL = import.meta.env.VITE_API_URL || ''

/**
 * Get the URL for a media file, preferring local path over CDN.
 * Local files are served via /api/files/{path}
 */
export function getMediaUrl(localPath: string | null | undefined, cdnUrl: string | null | undefined): string | null {
  // Prefer local path if available
  if (localPath) {
    return `${API_URL}/api/files/${localPath}`
  }
  // Fall back to CDN URL
  return cdnUrl || null
}

/**
 * Get image URL from video, preferring local.
 */
export function getImageUrl(video: { local_image_path?: string | null; image_url?: string | null }): string | null {
  return getMediaUrl(video.local_image_path, video.image_url)
}

/**
 * Get video URL from video, preferring local.
 */
export function getVideoUrl(video: { local_video_path?: string | null; video_url?: string | null }): string | null {
  return getMediaUrl(video.local_video_path, video.video_url)
}

/**
 * Get audio/video-with-audio URL from video, preferring local.
 */
export function getAudioUrl(video: { local_audio_path?: string | null; video_with_audio_url?: string | null }): string | null {
  return getMediaUrl(video.local_audio_path, video.video_with_audio_url)
}

/**
 * Get the best available video URL (audio version preferred, then video, then null).
 */
export function getBestVideoUrl(video: {
  local_audio_path?: string | null
  video_with_audio_url?: string | null
  local_video_path?: string | null
  video_url?: string | null
}): string | null {
  // First try audio version
  const audioUrl = getAudioUrl(video)
  if (audioUrl) return audioUrl

  // Fall back to video without audio
  return getVideoUrl(video)
}
