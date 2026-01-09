import { Volume2, CheckCircle, Loader2 } from 'lucide-react'

interface AudioVariantSelectorProps {
  variants: string[]
  selectedIndex: number | null
  onSelect: (index: number) => void
  onConfirm: () => void
  isLoading: boolean
}

export default function AudioVariantSelector({
  variants,
  selectedIndex,
  onSelect,
  onConfirm,
  isLoading,
}: AudioVariantSelectorProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Select your preferred audio variant:
      </p>
      <div className="grid grid-cols-2 gap-3">
        {variants.map((url, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(idx)}
            className={`relative p-4 rounded-lg border-2 transition ${
              selectedIndex === idx
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-purple-300'
            }`}
          >
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-full ${
                selectedIndex === idx ? 'bg-purple-500 text-white' : 'bg-gray-100 text-gray-600'
              }`}>
                <Volume2 className="h-4 w-4" />
              </div>
              <div className="text-left">
                <div className="font-medium">Variant {idx + 1}</div>
                <div className="text-xs text-gray-500">Click to preview</div>
              </div>
            </div>
            {selectedIndex === idx && (
              <CheckCircle className="absolute top-2 right-2 h-5 w-5 text-purple-500" />
            )}
            <audio src={url} className="mt-2 w-full" controls />
          </button>
        ))}
      </div>

      {selectedIndex !== null && (
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Selecting...
            </span>
          ) : (
            `Use Variant ${selectedIndex + 1}`
          )}
        </button>
      )}
    </div>
  )
}
