import { useState, useEffect, useCallback } from 'react'
import { templateApi } from '@/services/api'
import type { VideoTemplate, VideoTemplateCreate } from '@/types'

interface VideoTemplatesListProps {
  projectId: number
  refreshTrigger?: number
  onCountChange?: () => void
}

export function VideoTemplatesList({ projectId, refreshTrigger, onCountChange }: VideoTemplatesListProps) {
  const [templates, setTemplates] = useState<VideoTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create/Edit form
  const [showForm, setShowForm] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<VideoTemplate | null>(null)
  const [formData, setFormData] = useState<VideoTemplateCreate>({
    name: '',
    prompt: '',
    is_default: false,
  })
  const [saving, setSaving] = useState(false)

  const loadTemplates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await templateApi.listVideoTemplates(projectId)
      setTemplates(response.data)
      onCountChange?.()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to load templates'
        : 'Failed to load templates'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates, refreshTrigger])

  const handleCreate = () => {
    setEditingTemplate(null)
    setFormData({ name: '', prompt: '', is_default: false })
    setShowForm(true)
  }

  const handleEdit = (template: VideoTemplate) => {
    setEditingTemplate(template)
    setFormData({
      name: template.name,
      prompt: template.prompt,
      is_default: template.is_default,
    })
    setShowForm(true)
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingTemplate(null)
    setFormData({ name: '', prompt: '', is_default: false })
  }

  const handleSave = async () => {
    if (!formData.name.trim() || !formData.prompt.trim()) {
      alert('Name and prompt are required')
      return
    }

    setSaving(true)
    try {
      if (editingTemplate) {
        await templateApi.updateVideoTemplate(projectId, editingTemplate.id, formData)
      } else {
        await templateApi.createVideoTemplate(projectId, formData)
      }
      setShowForm(false)
      setEditingTemplate(null)
      setFormData({ name: '', prompt: '', is_default: false })
      loadTemplates()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to save'
        : 'Failed to save'
      alert(errorMsg)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (templateId: number) => {
    if (!confirm('Delete this video template?')) return
    try {
      await templateApi.deleteVideoTemplate(projectId, templateId)
      loadTemplates()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete'
        : 'Failed to delete'
      alert(errorMsg)
    }
  }

  const handleSetDefault = async (template: VideoTemplate) => {
    if (template.is_default) return
    try {
      await templateApi.updateVideoTemplate(projectId, template.id, { is_default: true })
      loadTemplates()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update'
        : 'Failed to update'
      alert(errorMsg)
    }
  }

  if (loading && templates.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <svg className="animate-spin h-6 w-6 text-gray-400" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Video Templates</h3>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Add Template
        </button>
      </div>

      {/* Create/Edit Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg mx-4">
            <h3 className="text-lg font-medium mb-4">
              {editingTemplate ? 'Edit Template' : 'New Template'}
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Template name"
                  maxLength={100}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Video Prompt Template
                </label>
                <textarea
                  value={formData.prompt}
                  onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={6}
                  placeholder="Video generation prompt with {placeholders}..."
                />
                <p className="mt-1 text-xs text-gray-500">
                  Use {'{column_name}'} to insert values from CSV variants
                </p>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="is_default" className="text-sm text-gray-700">
                  Set as default template
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Templates List */}
      {templates.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No video templates yet. Click "Add Template" to create one.
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map((template) => (
            <div
              key={template.id}
              className="border rounded-lg p-4 hover:bg-gray-50"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-gray-900">{template.name}</h4>
                    {template.is_default && (
                      <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                        Default
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                    {template.prompt}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {!template.is_default && (
                    <button
                      onClick={() => handleSetDefault(template)}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Set Default
                    </button>
                  )}
                  <button
                    onClick={() => handleEdit(template)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(template.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
