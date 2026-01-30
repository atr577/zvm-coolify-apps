import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import { templateApi, projectsApi, socialAccountsApi } from '@/services/api'
import type { TemplateSettings, TemplateSettingsUpdate, LLMModel, ImageModel, VideoModel, AspectRatio, SocialAccount } from '@/types'
import {
  LLM_MODELS,
  IMAGE_MODELS,
  VIDEO_MODELS,
  ASPECT_RATIOS,
  getDurationOptions,
  getDefaultDuration,
} from '@/constants/models'

interface TemplateSettingsFormProps {
  projectId: number
}

interface ProjectInfo {
  name: string
  description: string
  platforms: string[]
  workspace_id?: number
}

export function TemplateSettingsForm({ projectId }: TemplateSettingsFormProps) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [settings, setSettings] = useState<TemplateSettings | null>(null)

  // Project info state
  const [projectInfo, setProjectInfo] = useState<ProjectInfo>({
    name: '',
    description: '',
    platforms: [],
  })

  // Settings form state
  const [formData, setFormData] = useState<TemplateSettingsUpdate>({})

  // Social accounts state
  const [workspaceAccounts, setWorkspaceAccounts] = useState<SocialAccount[]>([])
  const [boundAccounts, setBoundAccounts] = useState<SocialAccount[]>([])
  const [bindingLoading, setBindingLoading] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)

      // Load project and settings in parallel
      const [settingsRes, projectRes] = await Promise.all([
        templateApi.getSettings(projectId),
        projectsApi.get(projectId),
      ])

      const project = projectRes.data
      setSettings(settingsRes.data)
      setProjectInfo({
        name: project.name,
        description: project.description || '',
        platforms: project.platforms || [],
        workspace_id: project.workspace_id,
      })
      setFormData({
        preprocessing_prompt: settingsRes.data.preprocessing_prompt,
        image_prompt_template: settingsRes.data.image_prompt_template,
        llm_model: settingsRes.data.llm_model as LLMModel,
        image_model: settingsRes.data.image_model as ImageModel,
        video_model: settingsRes.data.video_model as VideoModel,
        image_aspect_ratio: settingsRes.data.image_aspect_ratio as AspectRatio,
        video_duration: settingsRes.data.video_duration,
      })
      setBoundAccounts(project.social_accounts || [])

      // Load workspace accounts
      if (project.workspace_id) {
        const accountsRes = await socialAccountsApi.listByWorkspace(project.workspace_id)
        setWorkspaceAccounts(accountsRes.data)
      }
    } catch (err) {
      setError('Failed to load settings')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Get bound account for a platform
  const getBoundAccount = useCallback((platform: string) => {
    return boundAccounts.find(acc => acc.platform === platform && acc.is_active)
  }, [boundAccounts])

  // Bind/unbind account
  const handleBindAccount = async (platform: string, accountId: number | null) => {
    setBindingLoading(platform)
    try {
      const currentBound = getBoundAccount(platform)
      if (currentBound) {
        await projectsApi.unbindSocialAccount(projectId, currentBound.id)
      }
      if (accountId) {
        const res = await projectsApi.bindSocialAccount(projectId, accountId)
        setBoundAccounts(res.data.social_accounts)
        // Auto-enable platform
        if (!projectInfo.platforms.includes(platform)) {
          setProjectInfo(prev => ({ ...prev, platforms: [...prev.platforms, platform] }))
        }
      } else {
        setBoundAccounts(prev => prev.filter(acc => acc.platform !== platform))
      }
    } catch {
      // silently fail
    } finally {
      setBindingLoading(null)
    }
  }

  // togglePlatform removed - platforms derived from social accounts

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)

      // Save project info and settings in parallel
      await Promise.all([
        projectsApi.update(projectId, {
          name: projectInfo.name,
          description: projectInfo.description || undefined,
          platforms: projectInfo.platforms,
        }),
        templateApi.updateSettings(projectId, formData),
      ])

      navigate(`/?project=${projectId}`)
    } catch (err) {
      setError('Failed to save settings')
      console.error(err)
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

  if (!settings) {
    return (
      <div className="text-center py-12 text-red-600">
        {error || 'Settings not found'}
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
          Project Info
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

          {/* Platforms - HIDDEN: derived from social accounts */}
        </div>
      </section>

      {/* Social Accounts */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          Social Accounts
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Bind accounts to this project for publishing videos.
        </p>
        <div className="space-y-3">
          {['instagram', 'tiktok', 'youtube'].map(platform => {
            const platformAccounts = workspaceAccounts.filter(a => a.platform === platform && a.is_active)
            const bound = getBoundAccount(platform)
            const isLoading = bindingLoading === platform

            return (
              <div key={platform} className="border rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">{platform}</span>
                  {isLoading && <span className="text-xs text-gray-400">...</span>}
                </div>
                {platformAccounts.length === 0 ? (
                  <p className="text-xs text-gray-400 mt-1">No connected accounts</p>
                ) : (
                  <select
                    value={bound?.id || ''}
                    onChange={(e) => handleBindAccount(platform, e.target.value ? Number(e.target.value) : null)}
                    disabled={isLoading}
                    className="w-full mt-2 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    <option value="">Not selected</option>
                    {platformAccounts.map(acc => (
                      <option key={acc.id} value={acc.id} disabled={acc.is_token_expired}>
                        @{acc.username || acc.display_name || acc.platform_user_id}
                        {acc.is_token_expired ? ' (expired)' : ''}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )
          })}
        </div>
        <button
          type="button"
          onClick={() => window.open('/social-accounts', '_blank')}
          className="mt-3 flex items-center text-sm text-primary-600 hover:text-primary-700"
        >
          <ExternalLink className="h-3 w-3 mr-1" />
          Connect new account
        </button>
      </section>

      {/* LLM Settings */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          LLM Settings
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              LLM Model
            </label>
            <select
              value={formData.llm_model || ''}
              onChange={(e) => setFormData({ ...formData, llm_model: e.target.value as LLMModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {LLM_MODELS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Preprocessing Prompt
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Use <code className="bg-gray-100 px-1 rounded">{'{column_name}'}</code> placeholders from CSV columns
            </p>
            <textarea
              value={formData.preprocessing_prompt || ''}
              onChange={(e) => setFormData({ ...formData, preprocessing_prompt: e.target.value })}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
              placeholder="Enter preprocessing prompt..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Image Prompt Template
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Use <code className="bg-gray-100 px-1 rounded">{'{column_name}'}</code> placeholders and <code className="bg-gray-100 px-1 rounded">{'{preprocessed}'}</code> for LLM output
            </p>
            <textarea
              value={formData.image_prompt_template || ''}
              onChange={(e) => setFormData({ ...formData, image_prompt_template: e.target.value })}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
              placeholder="Enter image prompt template..."
            />
          </div>
        </div>
      </section>

      {/* Image Settings */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          Image Generation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Image Model
            </label>
            <select
              value={formData.image_model || ''}
              onChange={(e) => setFormData({ ...formData, image_model: e.target.value as ImageModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {IMAGE_MODELS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Aspect Ratio
            </label>
            <select
              value={formData.image_aspect_ratio || ''}
              onChange={(e) => setFormData({ ...formData, image_aspect_ratio: e.target.value as AspectRatio })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {ASPECT_RATIOS.map((ratio) => (
                <option key={ratio.value} value={ratio.value}>
                  {ratio.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Video Settings */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
          Video Generation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Video Model
            </label>
            <select
              value={formData.video_model || ''}
              onChange={(e) => {
                const newModel = e.target.value as VideoModel
                const newDuration = getDefaultDuration(newModel)
                setFormData({ ...formData, video_model: newModel, video_duration: newDuration })
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {VIDEO_MODELS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Duration
            </label>
            <select
              value={formData.video_duration || getDefaultDuration(formData.video_model)}
              onChange={(e) => setFormData({ ...formData, video_duration: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {getDurationOptions(formData.video_model).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* CSV Columns Info */}
      {settings.csv_columns && settings.csv_columns.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
            Available Placeholders
          </h2>
          <div className="flex flex-wrap gap-2">
            {settings.csv_columns.map((col) => (
              <code
                key={col}
                className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm cursor-pointer hover:bg-gray-200"
                onClick={() => navigator.clipboard.writeText(`{${col}}`)}
                title="Click to copy"
              >
                {`{${col}}`}
              </code>
            ))}
          </div>
        </section>
      )}

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
