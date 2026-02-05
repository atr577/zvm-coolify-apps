import { useState, useEffect, useRef } from 'react'
import { Loader2, Save, ArrowRight, Wand2 } from 'lucide-react'
import type { DiscoverExtraction } from '@/types'
import { discoverApi } from '@/services/api'
import { getErrorMessage } from '@/types'

interface ExtractionViewProps {
  projectId: number
  extraction: DiscoverExtraction | null
  onRefresh: () => void
  onCreateTemplate: () => void
}

export function ExtractionView({ projectId, extraction, onRefresh, onCreateTemplate }: ExtractionViewProps) {
  const [extracting, setExtracting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editedBase, setEditedBase] = useState(extraction?.edited_base_prompt || extraction?.base_prompt || '')
  const [editedVariation, setEditedVariation] = useState(extraction?.edited_variation_prompt || extraction?.variation_prompt || '')
  const autoExtractedRef = useRef(false)

  // Auto-extract on mount if no extraction exists
  useEffect(() => {
    if (!extraction && !autoExtractedRef.current && !extracting) {
      autoExtractedRef.current = true
      handleExtract()
    }
  }, [extraction])

  const handleExtract = async () => {
    setExtracting(true)
    setError(null)
    try {
      const res = await discoverApi.extract(projectId)
      const ext = res.data.extraction
      setEditedBase(ext.edited_base_prompt || ext.base_prompt)
      setEditedVariation(ext.edited_variation_prompt || ext.variation_prompt)
      onRefresh()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setExtracting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await discoverApi.updateExtraction(projectId, {
        edited_base_prompt: editedBase,
        edited_variation_prompt: editedVariation,
      })
      onRefresh()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  if (!extraction) {
    return (
      <div className="text-center py-12">
        <Wand2 className={`h-12 w-12 mx-auto mb-4 ${extracting ? 'text-purple-600 animate-pulse' : 'text-purple-400'}`} />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {extracting ? 'Extracting Template...' : 'Extract Template'}
        </h3>
        <p className="text-gray-500 mb-6 max-w-md mx-auto">
          {extracting
            ? 'AI is analyzing your winning prompts to create a reusable template...'
            : 'AI will analyze your winning image and video prompts to create a reusable template with variable slots.'
          }
        </p>
        {extracting ? (
          <Loader2 className="h-8 w-8 animate-spin text-purple-600 mx-auto" />
        ) : (
          <button
            onClick={handleExtract}
            disabled={extracting}
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            <Wand2 className="h-4 w-4" />
            Extract template
          </button>
        )}
        {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Winning prompts (read-only) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Winning Image Prompt</label>
          <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto">
            {extraction.winning_image_prompt}
          </div>
        </div>
        {extraction.winning_video_prompt && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Winning Video Prompt</label>
            <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto">
              {extraction.winning_video_prompt}
            </div>
          </div>
        )}
      </div>

      {/* Slots */}
      {extraction.slot_names && extraction.slot_names.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Template Slots</label>
          <div className="flex flex-wrap gap-2">
            {extraction.slot_names.map(slot => (
              <div key={slot} className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-1.5">
                <span className="text-sm font-mono text-purple-700">{`{${slot}}`}</span>
                {extraction.slot_examples?.[slot] && (
                  <span className="text-xs text-gray-500 ml-2">
                    e.g. {extraction.slot_examples[slot].slice(0, 3).join(', ')}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Editable prompts */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Base Prompt (template)</label>
        <textarea
          value={editedBase}
          onChange={(e) => setEditedBase(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono"
          rows={6}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Variation Prompt (for LLM)</label>
        <textarea
          value={editedVariation}
          onChange={(e) => setEditedVariation(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          rows={4}
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save edits
        </button>

        <button
          onClick={handleExtract}
          disabled={extracting}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 disabled:opacity-50"
        >
          {extracting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
          Re-extract
        </button>

        <button
          onClick={onCreateTemplate}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700"
        >
          <ArrowRight className="h-4 w-4" />
          Create Template Project
        </button>
      </div>
    </div>
  )
}
