import { useState } from 'react'
import { ContentVariant } from '@/types'
import { RefreshCw } from 'lucide-react'

interface VideoVariantSelectorProps {
  variants: ContentVariant[]
  onSelect: (variant: ContentVariant) => void
  onRegenerate: () => void
  isRegenerating: boolean
}

export default function VideoVariantSelector({
  variants,
  onSelect,
  onRegenerate,
  isRegenerating
}: VideoVariantSelectorProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const formatVariableValue = (value: any): string => {
    if (typeof value === 'object' && value !== null) {
      return Object.entries(value)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ')
    }
    return String(value)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Выберите вариант контента</h3>
        <button
          onClick={onRegenerate}
          disabled={isRegenerating}
          className="flex items-center space-x-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${isRegenerating ? 'animate-spin' : ''}`} />
          <span>Другие варианты</span>
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 max-h-[500px] overflow-y-auto">
        {variants.map((variant) => (
          <label
            key={variant.id}
            className={`
              flex items-start space-x-3 p-4 border-2 rounded-lg cursor-pointer transition
              ${selectedId === variant.id
                ? 'border-primary-600 bg-primary-50'
                : 'border-gray-200 hover:border-primary-300'
              }
            `}
          >
            <input
              type="radio"
              name="variant"
              checked={selectedId === variant.id}
              onChange={() => setSelectedId(variant.id)}
              className="mt-1"
            />
            <div className="flex-1">
              <p className="text-gray-900 font-medium mb-2">{variant.description}</p>

              {/* Детали */}
              <div className="space-y-1 text-sm text-gray-600">
                {variant.content_variables.character && (
                  <div className="flex">
                    <span className="font-semibold min-w-[80px]">Персонаж:</span>
                    <span className="flex-1">{formatVariableValue(variant.content_variables.character)}</span>
                  </div>
                )}
                {variant.content_variables.vehicle && (
                  <div className="flex">
                    <span className="font-semibold min-w-[80px]">Авто:</span>
                    <span className="flex-1">{formatVariableValue(variant.content_variables.vehicle)}</span>
                  </div>
                )}
                {variant.content_variables.location && (
                  <div className="flex">
                    <span className="font-semibold min-w-[80px]">Локация:</span>
                    <span className="flex-1">{formatVariableValue(variant.content_variables.location)}</span>
                  </div>
                )}
                {/* Любые другие переменные */}
                {Object.entries(variant.content_variables)
                  .filter(([key]) => !['character', 'vehicle', 'location'].includes(key))
                  .map(([key, value]) => (
                    <div key={key} className="flex">
                      <span className="font-semibold min-w-[80px] capitalize">{key}:</span>
                      <span className="flex-1">{formatVariableValue(value)}</span>
                    </div>
                  ))
                }
              </div>
            </div>
          </label>
        ))}
      </div>

      {variants.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Нет вариантов для отображения
        </div>
      )}

      <button
        onClick={() => {
          const selected = variants.find(v => v.id === selectedId)
          if (selected) onSelect(selected)
        }}
        disabled={!selectedId}
        className="w-full px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Выбрать
      </button>
    </div>
  )
}
