import { useEffect, useCallback } from 'react'
import { VIDEO_MODELS, getDurationOptions } from '@/constants/models'
import { templateApi } from '@/services/api'
import type { VideoModel } from '@/types'
import { VideoTemplatesList } from './VideoTemplatesList'

interface VideoStepProps {
  projectId: number
  videoModel: string
  videoDuration: string
  onModelChange: (model: string) => void
  onDurationChange: (duration: string) => void
  onTemplatesCountChange: (count: number) => void
}

export function VideoStep({
  projectId,
  videoModel,
  videoDuration,
  onModelChange,
  onDurationChange,
  onTemplatesCountChange,
}: VideoStepProps) {
  const durationOptions = getDurationOptions(videoModel)

  // Refresh templates count when component mounts or templates change
  const refreshCount = useCallback(async () => {
    try {
      const res = await templateApi.listVideoTemplates(projectId)
      onTemplatesCountChange(res.data.filter((t) => !t.is_deleted).length)
    } catch {
      // ignore
    }
  }, [projectId, onTemplatesCountChange])

  useEffect(() => {
    refreshCount()
  }, [refreshCount])

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Video Model
          </label>
          <select
            value={videoModel}
            onChange={(e) => onModelChange(e.target.value as VideoModel)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {VIDEO_MODELS.map((model) => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Duration
          </label>
          <select
            value={videoDuration}
            onChange={(e) => onDurationChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {durationOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="border-t pt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Video Templates</h4>
        <VideoTemplatesList projectId={projectId} onCountChange={refreshCount} />
      </div>
    </div>
  )
}
