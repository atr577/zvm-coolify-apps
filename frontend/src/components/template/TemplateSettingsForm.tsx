import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { templateApi } from '@/services/api'
import type { TemplateSettings, TemplateSettingsUpdate, LLMModel, ImageModel, VideoModel, AspectRatio } from '@/types'

interface TemplateSettingsFormProps {
  projectId: number
}

const LLM_MODELS: { value: LLMModel; label: string }[] = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (fast, cheap)' },
  { value: 'gpt-4o', label: 'GPT-4o (better quality)' },
]

const IMAGE_MODELS: { value: ImageModel; label: string }[] = [
  { value: 'fal-ai/nano-banana-pro', label: 'Nano Banana Pro (fast)' },
  { value: 'fal-ai/flux-pro/v1.1', label: 'Flux Pro v1.1' },
  { value: 'fal-ai/flux-pro/v1.1-ultra', label: 'Flux Pro Ultra (best)' },
  { value: 'fal-ai/ideogram/v3', label: 'Ideogram v3' },
  { value: 'fal-ai/imagen3', label: 'Imagen 3' },
]

const VIDEO_MODELS: { value: VideoModel; label: string }[] = [
  { value: 'fal-ai/veo3/fast/image-to-video', label: 'Veo3 Fast' },
  { value: 'fal-ai/veo3/image-to-video', label: 'Veo3' },
  { value: 'fal-ai/veo3.1/reference-to-video', label: 'Veo3.1 Reference' },
  { value: 'fal-ai/kling-video/v2.1/standard/image-to-video', label: 'Kling v2.1 Standard' },
  { value: 'fal-ai/kling-video/v2.1/pro/image-to-video', label: 'Kling v2.1 Pro' },
  { value: 'fal-ai/minimax/video-01', label: 'Minimax Video' },
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
    return [
      { value: '5s', label: '5 sec' },
    ]
  }

  // Default
  return [
    { value: '5', label: '5 sec' },
    { value: '6s', label: '6 sec' },
  ]
}

// Get default duration for model
const getDefaultDuration = (videoModel: string | undefined): string => {
  if (!videoModel) return '5'
  if (videoModel.includes('kling')) return '5'
  if (videoModel.includes('veo')) return '6s'
  if (videoModel.includes('minimax')) return '5s'
  return '5'
}

const ASPECT_RATIOS: { value: AspectRatio; label: string }[] = [
  { value: '9:16', label: '9:16 (Portrait / Reels)' },
  { value: '16:9', label: '16:9 (Landscape)' },
  { value: '1:1', label: '1:1 (Square)' },
]

export function TemplateSettingsForm({ projectId }: TemplateSettingsFormProps) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [settings, setSettings] = useState<TemplateSettings | null>(null)

  // Form state
  const [formData, setFormData] = useState<TemplateSettingsUpdate>({})

  useEffect(() => {
    loadSettings()
  }, [projectId])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await templateApi.getSettings(projectId)
      setSettings(response.data)
      setFormData({
        preprocessing_prompt: response.data.preprocessing_prompt,
        preprocessing_system_prompt: response.data.preprocessing_system_prompt || '',
        image_prompt_template: response.data.image_prompt_template,
        llm_model: response.data.llm_model as LLMModel,
        image_model: response.data.image_model as ImageModel,
        video_model: response.data.video_model as VideoModel,
        image_aspect_ratio: response.data.image_aspect_ratio as AspectRatio,
        video_duration: response.data.video_duration,
      })
    } catch (err) {
      setError('Failed to load settings')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      await templateApi.updateSettings(projectId, formData)
      navigate(`/?project=${projectId}`)
    } catch (err) {
      setError('Failed to save settings')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    navigate(`/?project=${projectId}`)
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="text-center py-12 text-red-600">
        {error || 'Settings not found'}
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* LLM Settings */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          LLM Settings
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              LLM Model
            </label>
            <select
              value={formData.llm_model || ''}
              onChange={(e) => setFormData({ ...formData, llm_model: e.target.value as LLMModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {LLM_MODELS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Preprocessing System Prompt
            </label>
            <p className="text-xs text-gray-500 mb-2">
              System prompt for preprocessing LLM call (optional)
            </p>
            <textarea
              value={formData.preprocessing_system_prompt || ''}
              onChange={(e) => setFormData({ ...formData, preprocessing_system_prompt: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
              placeholder="You are a creative assistant..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Preprocessing Prompt
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Use <code className="bg-gray-100 px-1 rounded">{'{column_name}'}</code> placeholders from CSV columns
            </p>
            <textarea
              value={formData.preprocessing_prompt || ''}
              onChange={(e) => setFormData({ ...formData, preprocessing_prompt: e.target.value })}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
              placeholder="Enter preprocessing prompt..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Image Prompt Template
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Use <code className="bg-gray-100 px-1 rounded">{'{column_name}'}</code> placeholders and <code className="bg-gray-100 px-1 rounded">{'{preprocessed}'}</code> for LLM output
            </p>
            <textarea
              value={formData.image_prompt_template || ''}
              onChange={(e) => setFormData({ ...formData, image_prompt_template: e.target.value })}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
              placeholder="Enter image prompt template..."
            />
          </div>
        </div>
      </section>

      {/* Image Settings */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          Image Generation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Image Model
            </label>
            <select
              value={formData.image_model || ''}
              onChange={(e) => setFormData({ ...formData, image_model: e.target.value as ImageModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {IMAGE_MODELS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Aspect Ratio
            </label>
            <select
              value={formData.image_aspect_ratio || ''}
              onChange={(e) => setFormData({ ...formData, image_aspect_ratio: e.target.value as AspectRatio })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {ASPECT_RATIOS.map((ratio) => (
                <option key={ratio.value} value={ratio.value}>
                  {ratio.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Video Settings */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          Video Generation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Video Model
            </label>
            <select
              value={formData.video_model || ''}
              onChange={(e) => {
                const newModel = e.target.value as VideoModel
                const newDuration = getDefaultDuration(newModel)
                setFormData({ ...formData, video_model: newModel, video_duration: newDuration })
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
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
              value={formData.video_duration || getDefaultDuration(formData.video_model)}
              onChange={(e) => setFormData({ ...formData, video_duration: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {getDurationOptions(formData.video_model).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* CSV Columns Info */}
      {settings.csv_columns && settings.csv_columns.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
            Available Placeholders
          </h2>
          <div className="flex flex-wrap gap-2">
            {settings.csv_columns.map((col) => (
              <code
                key={col}
                className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm cursor-pointer hover:bg-gray-200"
                onClick={() => navigator.clipboard.writeText(`{${col}}`)}
                title="Click to copy"
              >
                {`{${col}}`}
              </code>
            ))}
          </div>
        </section>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  )
}
