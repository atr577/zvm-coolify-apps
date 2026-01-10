import { Volume2, CheckCircle, Loader2 } from 'lucide-react'

interface AudioVariantSelectorProps {
  variants: string[]
  selectedIndex: number | null
  onSelect: (index: number) => void
  onConfirm: (index: number) => void
  isLoading: boolean
}

export default function AudioVariantSelector({
  variants,
  selectedIndex,
  onSelect,
  onConfirm,
  isLoading,
}: AudioVariantSelectorProps) {
  const currentIndex = selectedIndex ?? 0

  return (
    <div className="mb-6">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-4">
        {variants.map((_, index) => (
          <button
            key={index}
            onClick={() => onSelect(index)}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              currentIndex === index
                ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Volume2 className="h-4 w-4 inline mr-1" />
            Вариант {index + 1}
          </button>
        ))}
      </div>

      {/* Video Player */}
      <div className="flex justify-center mb-4">
        <div className="w-full max-w-sm">
          <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
            <video
              key={currentIndex}
              src={variants[currentIndex]}
              controls
              autoPlay
              className="w-full h-full object-contain"
            />
          </div>
        </div>
      </div>

      {/* Select Button */}
      <div className="flex justify-center">
        <button
          onClick={() => onConfirm(currentIndex)}
          disabled={isLoading}
          className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50 flex items-center"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Сохранение...
            </>
          ) : (
            <>
              <CheckCircle className="h-5 w-5 mr-2" />
              Выбрать вариант {currentIndex + 1}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
