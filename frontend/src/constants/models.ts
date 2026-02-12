/**
 * AI Model constants for Template projects.
 * Single source of truth for model options.
 */

import type { LLMModel, ImageModel, VideoModel, AspectRatio } from '@/types'

// --- LLM Models ---

export const LLM_MODELS: { value: LLMModel; label: string }[] = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4o', label: 'GPT-4o' },
]

// --- Image Models ---

export const IMAGE_MODELS: { value: ImageModel; label: string }[] = [
  { value: 'fal-ai/nano-banana-pro', label: 'Nano Banana Pro' },
  { value: 'fal-ai/flux-pro/v1.1', label: 'Flux Pro v1.1' },
  { value: 'fal-ai/flux-pro/v1.1-ultra', label: 'Flux Pro Ultra' },
  { value: 'fal-ai/ideogram/v3', label: 'Ideogram v3' },
  { value: 'fal-ai/imagen3', label: 'Imagen 3' },
]

// --- Video Models ---

export const VIDEO_MODELS: { value: VideoModel; label: string }[] = [
  { value: 'fal-ai/veo3/fast/image-to-video', label: 'Veo3 Fast' },
  { value: 'fal-ai/veo3/image-to-video', label: 'Veo3' },
  { value: 'fal-ai/veo3.1/reference-to-video', label: 'Veo3.1 Reference' },
  { value: 'fal-ai/kling-video/v3/standard/image-to-video', label: 'Kling v3 Standard' },
  { value: 'fal-ai/kling-video/v3/pro/image-to-video', label: 'Kling v3 Pro' },
  { value: 'fal-ai/kling-video/v2.1/standard/image-to-video', label: 'Kling v2.1 Standard' },
  { value: 'fal-ai/kling-video/v2.1/pro/image-to-video', label: 'Kling v2.1 Pro' },
  { value: 'fal-ai/minimax/video-01', label: 'Minimax Video-01' },
]

// --- Aspect Ratios ---

export const ASPECT_RATIOS: { value: AspectRatio; label: string }[] = [
  { value: '9:16', label: '9:16 (Portrait)' },
  { value: '16:9', label: '16:9 (Landscape)' },
  { value: '1:1', label: '1:1 (Square)' },
]

// --- Model Display Name ---

/**
 * Get human-readable model name from fal.ai model path.
 * Returns short label (e.g. "Flux Pro v1.1") or fallback to path segments.
 */
export function getModelDisplayName(modelPath: string | null | undefined): string | null {
  if (!modelPath) return null
  const imageMatch = IMAGE_MODELS.find(m => m.value === modelPath)
  if (imageMatch) return imageMatch.label
  const videoMatch = VIDEO_MODELS.find(m => m.value === modelPath)
  if (videoMatch) return videoMatch.label
  // Fallback: extract meaningful segments from path (skip "fal-ai" prefix)
  const segments = modelPath.split('/').filter(s => s !== 'fal-ai')
  return segments.join(' ') || modelPath
}

// --- Video Duration Helpers ---

/**
 * Get available duration options based on video model.
 * Different models support different durations.
 */
export function getDurationOptions(videoModel: string | undefined): { value: string; label: string }[] {
  if (!videoModel) return []

  if (videoModel.includes('kling')) {
    return [
      { value: '5', label: '5 sec' },
      { value: '10', label: '10 sec' },
    ]
  }

  if (videoModel.includes('veo')) {
    return [
      { value: '4s', label: '4 sec' },
      { value: '6s', label: '6 sec' },
      { value: '8s', label: '8 sec' },
    ]
  }

  if (videoModel.includes('minimax')) {
    return [{ value: '5s', label: '5 sec' }]
  }

  // Default
  return [
    { value: '5', label: '5 sec' },
    { value: '6s', label: '6 sec' },
  ]
}

/**
 * Get default duration for a video model.
 */
export function getDefaultDuration(videoModel: string | undefined): string {
  if (!videoModel) return '6s'
  if (videoModel.includes('kling')) return '5'
  if (videoModel.includes('veo')) return '6s'
  if (videoModel.includes('minimax')) return '5s'
  return '6s'
}
