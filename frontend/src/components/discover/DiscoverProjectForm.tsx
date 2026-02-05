import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import type { Workspace } from '@/types'

export interface DiscoverProjectFormData {
  name: string
  concept: string
  workspace_id: number
  image_model: string
  video_model: string
  image_aspect_ratio: string
}

interface DiscoverProjectFormProps {
  workspaces?: Workspace[]
  onSubmit: (data: DiscoverProjectFormData) => void
  onCancel: () => void
  isLoading: boolean
}

export function DiscoverProjectForm({ workspaces, onSubmit, onCancel, isLoading }: DiscoverProjectFormProps) {
  const [name, setName] = useState('')
  const [concept, setConcept] = useState('')
  const [workspaceId, setWorkspaceId] = useState<number>(workspaces?.[0]?.id || 0)
  const [imageModel] = useState('fal-ai/flux-pro/v1.1')
  const [videoModel] = useState('fal-ai/veo3/fast/image-to-video')
  const [aspectRatio, setAspectRatio] = useState('9:16')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !concept.trim() || !workspaceId) return
    onSubmit({
      name: name.trim(),
      concept: concept.trim(),
      workspace_id: workspaceId,
      image_model: imageModel,
      video_model: videoModel,
      image_aspect_ratio: aspectRatio,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Workspace */}
      {workspaces && workspaces.length > 1 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Workspace</label>
          <select
            value={workspaceId}
            onChange={(e) => setWorkspaceId(Number(e.target.value))}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          >
            {workspaces.map(w => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Project Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Scrap Crusher Discovery"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          required
        />
      </div>

      {/* Concept */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Concept</label>
        <textarea
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          placeholder="Describe your video concept in detail. E.g.: 'Heavy duty scrap shredder crusher destroying different objects — phones, laptops, toys. Close-up shots, satisfying destruction, vertical format.'"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          rows={4}
          required
          minLength={10}
        />
        <p className="text-xs text-gray-500 mt-1">Min 10 characters. Be as specific as possible.</p>
      </div>

      {/* Aspect ratio */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Aspect Ratio</label>
        <div className="flex gap-2">
          {['9:16', '16:9', '1:1'].map(ratio => (
            <button
              key={ratio}
              type="button"
              onClick={() => setAspectRatio(ratio)}
              className={`px-4 py-2 text-sm rounded-lg border transition ${
                aspectRatio === ratio
                  ? 'border-purple-500 bg-purple-50 text-purple-700'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {ratio}
            </button>
          ))}
        </div>
      </div>

      {/* Buttons */}
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading || !name.trim() || !concept.trim() || concept.trim().length < 10}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
          Create Discover Project
        </button>
      </div>
    </form>
  )
}
