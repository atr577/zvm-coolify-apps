import { useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { discoverApi } from '@/services/api'
import { getErrorMessage } from '@/types'

interface CreateTemplateModalProps {
  projectId: number
  defaultName: string
  extractedBasePrompt: string
  winningVideoPrompt: string
  onClose: () => void
  onCreated: (templateProjectId: number) => void
}

export function CreateTemplateModal({
  projectId,
  defaultName,
  extractedBasePrompt,
  winningVideoPrompt,
  onClose,
  onCreated,
}: CreateTemplateModalProps) {
  const [name, setName] = useState(defaultName)
  const [videoPrompt, setVideoPrompt] = useState(winningVideoPrompt || extractedBasePrompt)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCreate = async () => {
    if (!name.trim() || !videoPrompt.trim()) return
    setCreating(true)
    setError(null)
    try {
      const res = await discoverApi.createTemplate(projectId, {
        name: name.trim(),
        video_template_prompt: videoPrompt.trim(),
      })
      onCreated(res.data.project_id)
    } catch (err) {
      setError(getErrorMessage(err))
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full">
        <div className="flex items-center justify-between p-6 pb-4 border-b">
          <h2 className="text-xl font-semibold">Create Template Project</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Project Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Video Template Prompt</label>
            <textarea
              value={videoPrompt}
              onChange={(e) => setVideoPrompt(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono"
              rows={6}
            />
            <p className="text-xs text-gray-500 mt-1">This will be used as the video template prompt</p>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="flex justify-end gap-3 p-6 pt-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating || !name.trim() || !videoPrompt.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {creating && <Loader2 className="h-4 w-4 animate-spin" />}
            Create Template
          </button>
        </div>
      </div>
    </div>
  )
}
