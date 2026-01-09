import { useState, useEffect, useRef } from 'react'
import { Play } from 'lucide-react'

interface PlatformSelectorProps {
  initialPlatforms?: string[]
  onGenerate: (platforms: string[]) => void
  isLoading?: boolean
}

const PLATFORM_OPTIONS = [
  { value: 'instagram', label: 'Instagram Reels', icon: '📸' },
  { value: 'tiktok', label: 'TikTok', icon: '🎵' },
  { value: 'youtube', label: 'YouTube Shorts', icon: '📹' },
]

export default function PlatformSelector({ initialPlatforms = [], onGenerate, isLoading = false }: PlatformSelectorProps) {
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(initialPlatforms)
  const containerRef = useRef<HTMLDivElement>(null)
  const generateButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    // Scroll to this section when it appears
    containerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })

    // If platforms are already pre-selected, focus on the generate button
    if (initialPlatforms.length > 0) {
      setTimeout(() => {
        generateButtonRef.current?.focus()
      }, 500)
    }
  }, [])

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    )
  }

  const handleGenerate = () => {
    if (selectedPlatforms.length > 0) {
      onGenerate(selectedPlatforms)
    }
  }

  return (
    <div ref={containerRef} className="bg-white rounded-lg shadow p-6 space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Выберите платформы для адаптации:
        </label>
        <div className="flex flex-wrap gap-3">
          {PLATFORM_OPTIONS.map(platform => (
            <button
              key={platform.value}
              type="button"
              onClick={() => togglePlatform(platform.value)}
              disabled={isLoading}
              className={`px-4 py-3 rounded-lg transition flex items-center space-x-2 ${
                selectedPlatforms.includes(platform.value)
                  ? 'bg-primary-600 text-white shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <span className="text-xl">{platform.icon}</span>
              <span className="font-medium">{platform.label}</span>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Выбрано: {selectedPlatforms.length} {selectedPlatforms.length === 1 ? 'платформа' : 'платформ'}
        </p>
      </div>

      <button
        ref={generateButtonRef}
        onClick={handleGenerate}
        disabled={selectedPlatforms.length === 0 || isLoading}
        className="flex items-center px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            Генерация адаптаций...
          </>
        ) : (
          <>
            <Play className="h-5 w-5 mr-2" />
            Создать адаптации для выбранных платформ
          </>
        )}
      </button>
    </div>
  )
}
