import { useState } from 'react'
import { ContentVariant } from '@/types'
import { RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'

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
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  const toggleExpanded = (id: number, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const formatVariableValue = (value: unknown): string => {
    if (typeof value === 'object' && value !== null) {
      return Object.entries(value as Record<string, unknown>)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ')
    }
    return String(value)
  }

  const hasVariables = (v: ContentVariant) =>
    v.content_variables && Object.keys(v.content_variables).length > 0

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
        {variants.map((variant) => {
          const isExpanded = expandedIds.has(variant.id)
          return (
            <label
              key={variant.id}
              className={`
                block p-4 border-2 rounded-lg cursor-pointer transition
                ${selectedId === variant.id
                  ? 'border-primary-600 bg-primary-50'
                  : 'border-gray-200 hover:border-primary-300'
                }
              `}
            >
              <div className="flex items-start space-x-3">
                <input
                  type="radio"
                  name="variant"
                  checked={selectedId === variant.id}
                  onChange={() => setSelectedId(variant.id)}
                  className="mt-1"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-gray-900 font-medium">{variant.description}</p>

                  {/* Toggle для деталей */}
                  {hasVariables(variant) && (
                    <button
                      onClick={(e) => toggleExpanded(variant.id, e)}
                      className="mt-2 flex items-center text-xs text-gray-500 hover:text-gray-700"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-3 w-3 mr-1" />
                          Скрыть детали
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3 w-3 mr-1" />
                          Показать детали
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Детали - свернуты по умолчанию */}
              {isExpanded && hasVariables(variant) && (
                <div className="mt-3 ml-7 pt-3 border-t border-gray-200 space-y-1 text-sm text-gray-600">
                  {Object.entries(variant.content_variables).map(([key, value]) => (
                    <div key={key} className="flex">
                      <span className="font-medium min-w-[100px] capitalize text-gray-500">{key}:</span>
                      <span className="flex-1 text-gray-700">{formatVariableValue(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </label>
          )
        })}
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
