import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { CreateProjectDto, Workspace, AudioMode, SystemPrompts } from '@/types'

interface ProjectFormProps {
  initialData?: Partial<CreateProjectDto>
  workspaces?: Workspace[]
  onSubmit: (data: CreateProjectDto) => void
  onCancel: () => void
  isLoading: boolean
}

const AUDIO_MODES: { value: AudioMode; label: string; description: string }[] = [
  { value: 'none', label: 'Без звука', description: 'Видео без аудио' },
  { value: 'scene', label: 'Звуки сцены', description: 'Атмосферные звуки' },
  { value: 'music', label: 'Музыка', description: 'Фоновая музыка' },
  { value: 'voiceover', label: 'Озвучка', description: 'Голосовое сопровождение' },
  { value: 'auto', label: 'Авто', description: 'AI выберет подходящий режим' },
]

const STEP_PROMPTS: { key: keyof SystemPrompts; label: string }[] = [
  { key: 'story', label: 'Story Generation' },
  { key: 'description', label: 'Scene Description' },
  { key: 'prompt', label: 'Image Prompt' },
  { key: 'scenario', label: 'Video Scenario' },
  { key: 'adaptation', label: 'Platform Adaptation' },
]

export default function ProjectForm({
  initialData,
  workspaces,
  onSubmit,
  onCancel,
  isLoading
}: ProjectFormProps) {
  const [formData, setFormData] = useState<CreateProjectDto>({
    name: initialData?.name || '',
    description: initialData?.description || '',
    story_template: initialData?.story_template || '',
    platforms: initialData?.platforms || [],
    duration: initialData?.duration || 5,
    aspect_ratio: initialData?.aspect_ratio || '9:16',
    audio_mode: initialData?.audio_mode || 'auto',
    system_prompts: initialData?.system_prompts || {},
    workspace_id: initialData?.workspace_id || workspaces?.[0]?.id
  })
  const [showAdvanced, setShowAdvanced] = useState(false)

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
      {/* Название */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Название проекта *
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Девушки и авто"
          required
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
          Платформы *
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

      {/* Duration */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Длительность *
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
              <span>{duration} сек</span>
            </label>
          ))}
        </div>
      </div>

      {/* Aspect Ratio */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Формат видео *
        </label>
        <div className="flex space-x-4">
          {[
            { value: '9:16', label: '9:16 (вертикальный)' },
            { value: '16:9', label: '16:9 (горизонтальный)' },
            { value: '1:1', label: '1:1 (квадрат)' }
          ].map(ratio => (
            <label key={ratio.value} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="aspect_ratio"
                checked={formData.aspect_ratio === ratio.value}
                onChange={() => setFormData({ ...formData, aspect_ratio: ratio.value as '9:16' | '16:9' | '1:1' })}
                className="border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span>{ratio.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Story Template */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Story Template (концепция ролика) *
        </label>
        <textarea
          value={formData.story_template}
          onChange={(e) => setFormData({ ...formData, story_template: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          rows={6}
          placeholder="Элегантная девушка в стильном наряде выходит из роскошного автомобиля премиум класса на фоне узнаваемой локации мирового города..."
          required
        />
        <p className="mt-1 text-xs text-gray-500">
          Опишите общую концепцию ролика. AI сгенерирует множество конкретных вариантов на основе этого шаблона.
        </p>
      </div>

      {/* Audio Mode */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Режим звука
        </label>
        <div className="grid grid-cols-5 gap-2">
          {AUDIO_MODES.map(mode => (
            <label
              key={mode.value}
              className={`flex flex-col items-center p-2 border rounded-lg cursor-pointer transition ${
                formData.audio_mode === mode.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <input
                type="radio"
                name="audio_mode"
                value={mode.value}
                checked={formData.audio_mode === mode.value}
                onChange={() => setFormData({ ...formData, audio_mode: mode.value })}
                className="sr-only"
              />
              <span className="text-sm font-medium">{mode.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="border-t pt-4">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          {showAdvanced ? <ChevronDown className="h-4 w-4 mr-1" /> : <ChevronRight className="h-4 w-4 mr-1" />}
          Системные промпты (опционально)
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4">
            <p className="text-xs text-gray-500">
              Кастомные системные промпты для каждого этапа генерации. Оставьте пустым для использования промптов по умолчанию.
            </p>
            {STEP_PROMPTS.map(step => (
              <div key={step.key}>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  {step.label}
                </label>
                <textarea
                  value={formData.system_prompts?.[step.key] || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    system_prompts: {
                      ...formData.system_prompts,
                      [step.key]: e.target.value || undefined
                    }
                  })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={2}
                  placeholder={`Системный промпт для ${step.label}...`}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Buttons */}
      <div className="flex space-x-3">
        <button
          type="submit"
          disabled={isLoading || !formData.name || !formData.story_template || formData.platforms.length === 0}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Сохранение...' : 'Сохранить'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
        >
          Отмена
        </button>
      </div>
    </form>
  )
}
