import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { projectsApi, workspacesApi } from '@/services/api'
import type { Workspace } from '@/types'

interface TemplateSettingsFormProps {
  projectId: number
}

interface ProjectInfo {
  name: string
  description: string
  workspace_id?: number
}

export function TemplateSettingsForm({ projectId }: TemplateSettingsFormProps) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [projectInfo, setProjectInfo] = useState<ProjectInfo>({
    name: '',
    description: '',
  })

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [projectRes, workspacesRes] = await Promise.all([
        projectsApi.get(projectId),
        workspacesApi.list(),
      ])
      setWorkspaces(workspacesRes.data)
      const project = projectRes.data
      setProjectInfo({
        name: project.name,
        description: project.description || '',
        workspace_id: project.workspace_id,
      })
    } catch {
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      await projectsApi.update(projectId, {
        name: projectInfo.name,
        description: projectInfo.description || undefined,
        workspace_id: projectInfo.workspace_id,
      })
      navigate(`/?project=${projectId}`)
    } catch {
      setError('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    navigate(`/?project=${projectId}`)
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Project Info */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          Project Settings
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project Name
            </label>
            <input
              type="text"
              value={projectInfo.name}
              onChange={(e) => setProjectInfo({ ...projectInfo, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <input
              type="text"
              value={projectInfo.description}
              onChange={(e) => setProjectInfo({ ...projectInfo, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="Optional description"
            />
          </div>

          {workspaces.length > 1 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Workspace
              </label>
              <select
                value={projectInfo.workspace_id || ''}
                onChange={(e) =>
                  setProjectInfo({ ...projectInfo, workspace_id: Number(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    {ws.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </section>

      <p className="text-sm text-gray-500">
        Pipeline configuration (models, prompts, templates, social accounts, schedule) has moved to{' '}
        <button
          type="button"
          onClick={() => navigate(`/?project=${projectId}&screen=pipeline`)}
          className="text-primary-600 hover:underline"
        >
          Pipeline → Configure
        </button>
        .
      </p>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  )
}
