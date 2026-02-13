import { useState } from 'react'
import { Save, X, Loader2 } from 'lucide-react'

interface StickySaveBarProps {
  isDirty: boolean
  onSave: () => Promise<void>
  onDiscard: () => void
}

export function StickySaveBar({ isDirty, onSave, onDiscard }: StickySaveBarProps) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isDirty) return null

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      await onSave()
    } catch (err) {
      console.error('Failed to save:', err)
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Failed to save: ${message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 shadow-lg">
      <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">Unsaved changes</span>
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onDiscard}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition"
          >
            <X className="w-4 h-4" />
            Discard
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
