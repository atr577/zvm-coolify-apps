import { useState, useEffect } from 'react'
import { templateApi } from '@/services/api'
import type { Variant, VideoTemplate, Generation } from '@/types'

interface GenerationPanelProps {
  projectId: number
  onGenerationStarted: (generation: Generation) => void
}

export function GenerationPanel({ projectId, onGenerationStarted }: GenerationPanelProps) {
  const [variants, setVariants] = useState<Variant[]>([])
  const [templates, setTemplates] = useState<VideoTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  // Selection state
  const [selectedVariantId, setSelectedVariantId] = useState<number | undefined>(undefined)
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | undefined>(undefined)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [variantsRes, templatesRes] = await Promise.all([
        templateApi.listVariants(projectId, { limit: 100 }),
        templateApi.listVideoTemplates(projectId)
      ])
      setVariants(variantsRes.data.variants)
      setTemplates(templatesRes.data)

      // Pre-select default template
      const defaultTemplate = templatesRes.data.find(t => t.is_default)
      if (defaultTemplate) {
        setSelectedTemplateId(defaultTemplate.id)
      }
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const response = await templateApi.startGeneration(projectId, {
        variant_id: selectedVariantId,
        video_template_id: selectedTemplateId,
      })
      onGenerationStarted(response.data)
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Generation failed'
        : 'Generation failed'
      alert(errorMsg)
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center justify-center py-4">
          <svg className="animate-spin h-6 w-6 text-gray-400" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      </div>
    )
  }

  const canGenerate = variants.length > 0 && templates.length > 0

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Generate Video</h3>

      {!canGenerate ? (
        <div className="text-center py-4">
          <p className="text-gray-500">
            {variants.length === 0 && 'Upload a CSV with variants first.'}
            {variants.length > 0 && templates.length === 0 && 'Create a video template first.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Variant Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Variant
            </label>
            <select
              value={selectedVariantId || ''}
              onChange={(e) => setSelectedVariantId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Auto-select (least used)</option>
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  #{v.row_number} - {Object.values(v.data).slice(0, 2).join(', ')} (used {v.usage_count}x)
                </option>
              ))}
            </select>
          </div>

          {/* Template Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Template
            </label>
            <select
              value={selectedTemplateId || ''}
              onChange={(e) => setSelectedTemplateId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Use default template</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} {t.is_default && '(default)'}
                </option>
              ))}
            </select>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {generating ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting...
              </span>
            ) : (
              'Generate Video'
            )}
          </button>
        </div>
      )}
    </div>
  )
}
