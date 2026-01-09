import { useState } from 'react'
import { CreateProjectDto } from '@/types'

interface ProjectFormProps {
  initialData?: Partial<CreateProjectDto>
  onSubmit: (data: CreateProjectDto) => void
  onCancel: () => void
  isLoading: boolean
}

export default function ProjectForm({
  initialData,
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
    aspect_ratio: initialData?.aspect_ratio || '9:16'
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

      {/* Описание */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Описание (опционально)
        </label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          rows={2}
          placeholder="Роскошные девушки у премиум авто в мировых столицах"
        />
      </div>

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
