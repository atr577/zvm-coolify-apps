import { useState, useEffect } from 'react'
import { templateApi } from '@/services/api'
import type { Variant, VideoTemplate, BatchGenerateResponse, BatchMode } from '@/types'
import { Play, Loader2 } from 'lucide-react'

interface GenerationPanelProps {
  projectId: number
  onBatchStarted: (response: BatchGenerateResponse) => void
}

export function GenerationPanel({ projectId, onBatchStarted }: GenerationPanelProps) {
  const [variants, setVariants] = useState<Variant[]>([])
  const [templates, setTemplates] = useState<VideoTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  // Selection state
  const [mode, setMode] = useState<BatchMode>('all_unused')
  const [leastUsedCount, setLeastUsedCount] = useState(10)
  const [selectedVariantIds, setSelectedVariantIds] = useState<Set<number>>(new Set())
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | undefined>(undefined)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [variantsRes, templatesRes] = await Promise.all([
        templateApi.listVariants(projectId, { limit: 200 }),
        templateApi.listVideoTemplates(projectId)
      ])
      setVariants(variantsRes.data.variants)
      setTemplates(templatesRes.data)

      // Pre-select default template
      const defaultTemplate = templatesRes.data.find((t: VideoTemplate) => t.is_default)
      if (defaultTemplate) {
        setSelectedTemplateId(defaultTemplate.id)
      }
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  const unusedCount = variants.filter(v => v.usage_count === 0).length

  const getRunCount = (): number => {
    if (mode === 'all_unused') return unusedCount
    if (mode === 'least_used') return Math.min(leastUsedCount, variants.length)
    if (mode === 'specific') return selectedVariantIds.size
    return 0
  }

  const runCount = getRunCount()

  const handleGenerate = async () => {
    if (runCount === 0) return
    setGenerating(true)
    try {
      const response = await templateApi.startBatchGeneration(projectId, {
        mode,
        count: mode === 'least_used' ? leastUsedCount : undefined,
        variant_ids: mode === 'specific' ? Array.from(selectedVariantIds) : undefined,
        video_template_id: selectedTemplateId,
      })
      onBatchStarted(response.data)
      // Reload variants to update usage counts
      const variantsRes = await templateApi.listVariants(projectId, { limit: 200 })
      setVariants(variantsRes.data.variants)
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Batch generation failed'
        : 'Batch generation failed'
      alert(errorMsg)
    } finally {
      setGenerating(false)
    }
  }

  const toggleVariant = (id: number) => {
    setSelectedVariantIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  const canGenerate = variants.length > 0 && templates.length > 0

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Run Pipeline</h3>

      {!canGenerate ? (
        <div className="text-center py-4">
          <p className="text-gray-500">
            {variants.length === 0 && 'Upload variants in Configure → Input first.'}
            {variants.length > 0 && templates.length === 0 && 'Create a video template in Configure → Video first.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Variant Selection Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select variants
            </label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  checked={mode === 'all_unused'}
                  onChange={() => setMode('all_unused')}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">
                  All unused
                  <span className="text-gray-400 ml-1">({unusedCount})</span>
                </span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  checked={mode === 'least_used'}
                  onChange={() => setMode('least_used')}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">Least used, top</span>
                <input
                  type="number"
                  value={leastUsedCount}
                  onChange={(e) => setLeastUsedCount(Math.max(1, Math.min(200, Number(e.target.value))))}
                  onClick={() => setMode('least_used')}
                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                  min={1}
                  max={200}
                />
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  checked={mode === 'specific'}
                  onChange={() => setMode('specific')}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">
                  Specific variants
                  {mode === 'specific' && selectedVariantIds.size > 0 && (
                    <span className="text-gray-400 ml-1">({selectedVariantIds.size} selected)</span>
                  )}
                </span>
              </label>
            </div>

            {/* Specific variants list */}
            {mode === 'specific' && (
              <div className="mt-2 max-h-48 overflow-y-auto border rounded-lg p-2 space-y-1">
                {variants.map((v) => (
                  <label key={v.id} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-gray-50 px-1 py-0.5 rounded">
                    <input
                      type="checkbox"
                      checked={selectedVariantIds.has(v.id)}
                      onChange={() => toggleVariant(v.id)}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-gray-400">#{v.row_number}</span>
                    <span className="truncate">{Object.values(v.data).slice(0, 2).join(', ')}</span>
                    <span className="text-gray-400 ml-auto flex-shrink-0">{v.usage_count}x</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Template Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Template
            </label>
            <select
              value={selectedTemplateId || ''}
              onChange={(e) => setSelectedTemplateId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">Use default template</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} {t.is_default && '(default)'}
                </option>
              ))}
            </select>
          </div>

          {/* Run Button */}
          <button
            onClick={handleGenerate}
            disabled={generating || runCount === 0}
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                Run — {runCount} video{runCount !== 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
