import { useState } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { CsvUpload } from './CsvUpload'
import { VariantsList } from './VariantsList'
import { templateApi } from '@/services/api'
import type { CSVUploadResponse } from '@/types'

interface InputStepProps {
  projectId: number
  refreshTrigger: number
  variantGenerationPrompt: string
  onPromptChange: (value: string) => void
  onCsvUploadSuccess: (response: CSVUploadResponse) => void
  onVariantsGenerated: () => void
}

export function InputStep({
  projectId,
  refreshTrigger,
  variantGenerationPrompt,
  onPromptChange,
  onCsvUploadSuccess,
  onVariantsGenerated,
}: InputStepProps) {
  const [count, setCount] = useState(10)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [preview, setPreview] = useState<{ variants: Record<string, unknown>[]; columns: string[] } | null>(null)
  const [saveResult, setSaveResult] = useState<{ created: number; skipped: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const hasPrompt = !!variantGenerationPrompt

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      const res = await templateApi.generateVariantPrompt(projectId)
      onPromptChange(res.data.prompt)
    } catch (err) {
      console.error('Failed to regenerate variant prompt:', err)
    } finally {
      setRegenerating(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setError(null)
    setPreview(null)
    setSaveResult(null)
    try {
      const res = await templateApi.generateVariantsPreview(projectId, count)
      setPreview(res.data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Generation failed'
      setError(msg)
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async () => {
    if (!preview) return
    setSaving(true)
    setError(null)
    try {
      const res = await templateApi.saveGeneratedVariants(projectId, preview.variants)
      setSaveResult({ created: res.data.variants_created, skipped: res.data.duplicates_skipped })
      setPreview(null)
      onVariantsGenerated()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Save failed'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDiscard = () => {
    setPreview(null)
    setSaveResult(null)
  }

  return (
    <div className="space-y-4">
      {/* Generation prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-gray-700">
            Generation prompt
          </label>
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 flex items-center gap-1"
          >
            {regenerating && <Loader2 className="w-3 h-3 animate-spin" />}
            {regenerating ? 'Regenerating...' : 'Regenerate from pipeline'}
          </button>
        </div>
        <textarea
          value={variantGenerationPrompt}
          onChange={(e) => onPromptChange(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
          placeholder="Describe how to generate variant data rows... (auto-generated from pipeline prompts on first save)"
        />
      </div>

      {/* AI Generate */}
      <div className="border border-blue-100 bg-blue-50/50 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-900">Generate with AI</span>
        </div>

        {!preview ? (
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Count:</label>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
              disabled={generating}
            >
              {[5, 10, 20, 30, 50].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <button
              onClick={handleGenerate}
              disabled={!hasPrompt || generating}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {generating && <Loader2 className="w-3 h-3 animate-spin" />}
              {generating ? 'Generating...' : 'Generate variants'}
            </button>
            {!hasPrompt && (
              <span className="text-xs text-gray-400">Set generation prompt above first</span>
            )}
          </div>
        ) : (
          /* Preview table */
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">
              Preview ({preview.variants.length} new variants)
            </div>
            <div className="overflow-x-auto max-h-64 overflow-y-auto border border-gray-200 rounded bg-white">
              <table className="min-w-full text-xs">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-2 py-1.5 text-left font-medium text-gray-500">#</th>
                    {preview.columns.map((col) => (
                      <th key={col} className="px-2 py-1.5 text-left font-medium text-gray-500">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {preview.variants.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-2 py-1.5 text-gray-400">{i + 1}</td>
                      {preview.columns.map((col) => (
                        <td key={col} className="px-2 py-1.5 text-gray-700 max-w-[200px] truncate">
                          {typeof row[col] === 'object' && row[col] !== null
                            ? JSON.stringify(row[col])
                            : String(row[col] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-end gap-2 mt-3">
              <button
                onClick={handleDiscard}
                disabled={saving}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg"
              >
                Discard
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
              >
                {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                Save all {preview.variants.length}
              </button>
            </div>
          </div>
        )}

        {error && (
          <p className="text-xs text-red-500 mt-2">{error}</p>
        )}
        {saveResult && (
          <p className="text-xs text-green-600 mt-2">
            Created {saveResult.created} variants
            {saveResult.skipped > 0 && ` (${saveResult.skipped} duplicates skipped)`}
          </p>
        )}
      </div>

      {/* Separator */}
      <div className="flex items-center gap-3">
        <div className="flex-1 border-t border-gray-200" />
        <span className="text-xs text-gray-400">or upload CSV</span>
        <div className="flex-1 border-t border-gray-200" />
      </div>

      {/* CSV Upload */}
      <CsvUpload projectId={projectId} onUploadSuccess={onCsvUploadSuccess} />

      {/* Variants List */}
      <VariantsList projectId={projectId} refreshTrigger={refreshTrigger} />
    </div>
  )
}
