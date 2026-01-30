import { useState } from 'react'
import type { Workspace, AspectRatio, LLMModel, ImageModel, VideoModel } from '@/types'

export interface TemplateProjectCreateDto {
  name: string
  description?: string
  preprocessing_prompt: string
  image_prompt_template: string
  llm_model: LLMModel
  image_model: ImageModel
  video_model: VideoModel
  image_aspect_ratio: AspectRatio
  video_duration: string
  video_template_name: string
  video_template_prompt: string
  duration: number
  platforms: string[]
  workspace_id?: number
}

interface TemplateProjectFormProps {
  workspaces?: Workspace[]
  onSubmit: (data: TemplateProjectCreateDto) => void
  onCancel: () => void
  isLoading: boolean
}

const LLM_MODELS: { value: LLMModel; label: string }[] = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (fast, cheap)' },
  { value: 'gpt-4o', label: 'GPT-4o (better quality)' },
]

const IMAGE_MODELS: { value: ImageModel; label: string }[] = [
  { value: 'fal-ai/nano-banana-pro', label: 'Nano Banana Pro (fast)' },
  { value: 'fal-ai/flux-pro/v1.1', label: 'Flux Pro v1.1' },
  { value: 'fal-ai/flux-pro/v1.1-ultra', label: 'Flux Pro v1.1 Ultra' },
  { value: 'fal-ai/ideogram/v3', label: 'Ideogram v3' },
  { value: 'fal-ai/imagen3', label: 'Imagen 3' },
]

const VIDEO_MODELS: { value: VideoModel; label: string }[] = [
  { value: 'fal-ai/veo3/fast/image-to-video', label: 'Veo3 Fast' },
  { value: 'fal-ai/veo3/image-to-video', label: 'Veo3' },
  { value: 'fal-ai/veo3.1/reference-to-video', label: 'Veo3.1 Reference' },
  { value: 'fal-ai/kling-video/v2.1/standard/image-to-video', label: 'Kling v2.1 Standard' },
  { value: 'fal-ai/kling-video/v2.1/pro/image-to-video', label: 'Kling v2.1 Pro' },
  { value: 'fal-ai/minimax/video-01', label: 'Minimax Video-01' },
]

// Duration options per model type
const getDurationOptions = (videoModel: string | undefined): { value: string; label: string }[] => {
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
  return [{ value: '5', label: '5 sec' }, { value: '6s', label: '6 sec' }]
}

const getDefaultDuration = (videoModel: string | undefined): string => {
  if (!videoModel) return '6s'
  if (videoModel.includes('kling')) return '5'
  if (videoModel.includes('veo')) return '6s'
  if (videoModel.includes('minimax')) return '5s'
  return '6s'
}

export function TemplateProjectForm({
  workspaces,
  onSubmit,
  onCancel,
  isLoading
}: TemplateProjectFormProps) {
  const [formData, setFormData] = useState<TemplateProjectCreateDto>({
    name: '',
    description: '',
    preprocessing_prompt: '',
    image_prompt_template: '',
    llm_model: 'gpt-4o-mini',
    image_model: 'fal-ai/nano-banana-pro',
    video_model: 'fal-ai/veo3/fast/image-to-video',
    image_aspect_ratio: '9:16',
    video_duration: '6s',
    video_template_name: 'Default',
    video_template_prompt: '',
    duration: 10,
    platforms: [],
    workspace_id: workspaces?.[0]?.id
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const togglePlatform = (platform: string) => {
    setFormData(prev => ({
      ...prev,
      platforms: prev.platforms.includes(platform)
        ? prev.platforms.filter(p => p !== platform)
        : [...prev.platforms, platform]
    }))
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Project Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Project Name *
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="My Template Project"
          required
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description
        </label>
        <input
          type="text"
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Optional description"
        />
      </div>

      {/* Workspace */}
      {workspaces && workspaces.length > 1 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Workspace
          </label>
          <select
            value={formData.workspace_id || ''}
            onChange={(e) => setFormData({ ...formData, workspace_id: Number(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {workspaces.map(ws => (
              <option key={ws.id} value={ws.id}>{ws.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Platforms */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Platforms *
        </label>
        <div className="flex space-x-4">
          {['instagram', 'tiktok', 'youtube'].map(platform => (
            <label key={platform} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.platforms.includes(platform)}
                onChange={() => togglePlatform(platform)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="capitalize">{platform}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Duration & Aspect Ratio */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Duration *
          </label>
          <div className="flex space-x-4">
            {[5, 10, 15].map(duration => (
              <label key={duration} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="duration"
                  checked={formData.duration === duration}
                  onChange={() => setFormData({ ...formData, duration })}
                  className="border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span>{duration}s</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Aspect Ratio *
          </label>
          <div className="flex space-x-4">
            {[
              { value: '9:16', label: '9:16' },
              { value: '16:9', label: '16:9' },
              { value: '1:1', label: '1:1' }
            ].map(ratio => (
              <label key={ratio.value} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="aspect_ratio"
                  checked={formData.image_aspect_ratio === ratio.value}
                  onChange={() => setFormData({ ...formData, image_aspect_ratio: ratio.value as AspectRatio })}
                  className="border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span>{ratio.label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Model Selection */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">AI Models</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              LLM Model
            </label>
            <select
              value={formData.llm_model}
              onChange={(e) => setFormData({ ...formData, llm_model: e.target.value as LLMModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {LLM_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Image Model
            </label>
            <select
              value={formData.image_model}
              onChange={(e) => setFormData({ ...formData, image_model: e.target.value as ImageModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {IMAGE_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Model
            </label>
            <select
              value={formData.video_model}
              onChange={(e) => {
                const newModel = e.target.value as VideoModel
                const newDuration = getDefaultDuration(newModel)
                setFormData({ ...formData, video_model: newModel, video_duration: newDuration })
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {VIDEO_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Duration
            </label>
            <select
              value={formData.video_duration}
              onChange={(e) => setFormData({ ...formData, video_duration: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {getDurationOptions(formData.video_model).map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Prompts */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Prompts</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preprocessing Prompt *
            </label>
            <textarea
              value={formData.preprocessing_prompt}
              onChange={(e) => setFormData({ ...formData, preprocessing_prompt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={4}
              placeholder="Given this data: {location}, {car}, {model}... Generate a creative scene description."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              LLM prompt for preprocessing variant data. Use {'{column_name}'} for CSV placeholders.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Image Prompt Template *
            </label>
            <textarea
              value={formData.image_prompt_template}
              onChange={(e) => setFormData({ ...formData, image_prompt_template: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={4}
              placeholder="A beautiful woman in {clothes} next to a {car} in {location}..."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Template for image generation prompt. Use {'{column_name}'} and {'{preprocessing_result}'}.
            </p>
          </div>
        </div>
      </div>

      {/* Video Template */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Default Video Template</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Template Name *
            </label>
            <input
              type="text"
              value={formData.video_template_name}
              onChange={(e) => setFormData({ ...formData, video_template_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Default"
              maxLength={100}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Prompt Template *
            </label>
            <textarea
              value={formData.video_template_prompt}
              onChange={(e) => setFormData({ ...formData, video_template_prompt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={3}
              placeholder="Camera slowly pans around the scene, cinematic motion..."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Template for video generation prompt.
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end space-x-4 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {isLoading ? 'Creating...' : 'Create Project'}
        </button>
      </div>
    </form>
  )
}
