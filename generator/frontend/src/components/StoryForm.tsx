import { useState, useEffect, useRef } from 'react'
import { Sparkles } from 'lucide-react'

interface StoryFormProps {
  onSubmit: (data: StoryFormData) => void
  isLoading: boolean
}

export interface StoryFormData {
  theme?: string
  target_audience?: string
  mood?: string
  key_elements?: string
  duration: number
  platforms?: string[]
  additional_notes?: string
}

const PLATFORM_OPTIONS = [
  { value: 'instagram', label: 'Instagram Reels' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'youtube', label: 'YouTube Shorts' },
]

const MOOD_OPTIONS = [
  'Драматично',
  'Весело',
  'Мотивационно',
  'Эпично',
  'Загадочно',
  'Романтично',
  'Энергично',
  'Спокойно'
]

export default function StoryForm({ onSubmit, isLoading }: StoryFormProps) {
  const [formData, setFormData] = useState<StoryFormData>({
    theme: '',
    target_audience: '',
    mood: '',
    key_elements: '',
    duration: 5,
    platforms: [],
    additional_notes: '',
  })

  const themeInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Auto-focus on the first input field when form is shown
    themeInputRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const togglePlatform = (platform: string) => {
    setFormData(prev => ({
      ...prev,
      platforms: prev.platforms?.includes(platform)
        ? prev.platforms.filter(p => p !== platform)
        : [...(prev.platforms || []), platform]
    }))
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center mb-6">
        <Sparkles className="h-6 w-6 text-primary-600 mr-2" />
        <h3 className="text-xl font-bold text-gray-900">
          Вводные параметры для генерации сюжета
        </h3>
      </div>

      <div className="space-y-4">
        {/* Тема */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Тема / Ниша
          </label>
          <input
            ref={themeInputRef}
            type="text"
            value={formData.theme}
            onChange={(e) => setFormData({ ...formData, theme: e.target.value })}
            placeholder="Например: авто, мода, технологии, lifestyle, фитнес..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">Основная тематика видео</p>
        </div>

        {/* Целевая аудитория */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Целевая аудитория
          </label>
          <input
            type="text"
            value={formData.target_audience}
            onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
            placeholder="Например: мужчины 25-35, автолюбители, молодежь..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">Кто будет смотреть это видео</p>
        </div>

        {/* Настроение */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Настроение / Стиль
          </label>
          <select
            value={formData.mood}
            onChange={(e) => setFormData({ ...formData, mood: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">Выберите настроение...</option>
            {MOOD_OPTIONS.map(mood => (
              <option key={mood} value={mood}>{mood}</option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">Эмоциональная окраска видео</p>
        </div>

        {/* Ключевые элементы */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Обязательные элементы
          </label>
          <input
            type="text"
            value={formData.key_elements}
            onChange={(e) => setFormData({ ...formData, key_elements: e.target.value })}
            placeholder="Например: спорткар, закат, городская локация..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">Что обязательно должно быть в видео</p>
        </div>

        {/* Длительность */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Длительность видео
          </label>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                value={5}
                checked={formData.duration === 5}
                onChange={(e) => setFormData({ ...formData, duration: Number(e.target.value) })}
                className="mr-2"
              />
              <span>5 секунд</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value={10}
                checked={formData.duration === 10}
                onChange={(e) => setFormData({ ...formData, duration: Number(e.target.value) })}
                className="mr-2"
              />
              <span>10 секунд</span>
            </label>
          </div>
        </div>

        {/* Платформы */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Целевые платформы
          </label>
          <div className="flex flex-wrap gap-2">
            {PLATFORM_OPTIONS.map(platform => (
              <button
                key={platform.value}
                type="button"
                onClick={() => togglePlatform(platform.value)}
                className={`px-4 py-2 rounded-md transition ${
                  formData.platforms?.includes(platform.value)
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {platform.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1">Где планируется публикация</p>
        </div>

        {/* Дополнительные заметки */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Дополнительные указания (опционально)
          </label>
          <textarea
            value={formData.additional_notes}
            onChange={(e) => setFormData({ ...formData, additional_notes: e.target.value })}
            placeholder="Любые дополнительные детали, идеи, референсы..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            rows={3}
          />
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="submit"
          disabled={isLoading}
          className="flex items-center px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Генерируем...
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5 mr-2" />
              Сгенерировать сюжет
            </>
          )}
        </button>
      </div>
    </form>
  )
}
