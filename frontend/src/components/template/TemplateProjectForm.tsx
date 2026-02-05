import { useState, useEffect } from 'react'
import { ExternalLink } from 'lucide-react'
import type { Workspace, AspectRatio, LLMModel, ImageModel, VideoModel, SocialAccount } from '@/types'
import { socialAccountsApi } from '@/services/api'
import {
  LLM_MODELS,
  IMAGE_MODELS,
  VIDEO_MODELS,
  ASPECT_RATIOS,
  getDurationOptions,
  getDefaultDuration,
} from '@/constants/models'

export interface TemplateProjectCreateDto {
  name: string
  description?: string
  preprocessing_prompt: string
  image_prompt_template: string
  llm_model: LLMModel
  image_model: ImageModel
  video_model: VideoModel
  image_aspect_ratio: AspectRatio
  video_duration: string
  video_template_name: string
  video_template_prompt: string
  platforms: string[]
  workspace_id?: number
  social_account_ids?: number[]
}

interface TemplateProjectFormProps {
  workspaces?: Workspace[]
  onSubmit: (data: TemplateProjectCreateDto) => void
  onCancel: () => void
  isLoading: boolean
}

export function TemplateProjectForm({
  workspaces,
  onSubmit,
  onCancel,
  isLoading
}: TemplateProjectFormProps) {
  const [formData, setFormData] = useState<TemplateProjectCreateDto>({
    name: '',
    description: '',
    preprocessing_prompt: '',
    image_prompt_template: '',
    llm_model: 'gpt-4o-mini',
    image_model: 'fal-ai/nano-banana-pro',
    video_model: 'fal-ai/veo3/fast/image-to-video',
    image_aspect_ratio: '9:16',
    video_duration: '6s',
    video_template_name: 'Default',
    video_template_prompt: '',
    platforms: [],
    workspace_id: workspaces?.[0]?.id,
    social_account_ids: []
  })

  // Social accounts state
  const [workspaceAccounts, setWorkspaceAccounts] = useState<SocialAccount[]>([])
  const [selectedAccounts, setSelectedAccounts] = useState<Record<string, number | null>>({
    instagram: null,
    tiktok: null,
    youtube: null
  })

  // Load workspace accounts when workspace changes
  useEffect(() => {
    const workspaceId = formData.workspace_id || workspaces?.[0]?.id
    if (workspaceId) {
      socialAccountsApi.listByWorkspace(workspaceId)
        .then(res => setWorkspaceAccounts(res.data))
        .catch(() => setWorkspaceAccounts([]))
    }
  }, [formData.workspace_id, workspaces])

  // Update social_account_ids and platforms when selection changes
  useEffect(() => {
    const ids = Object.values(selectedAccounts).filter((id): id is number => id !== null)
    const platforms = Object.entries(selectedAccounts)
      .filter(([, id]) => id !== null)
      .map(([platform]) => platform)

    setFormData(prev => ({
      ...prev,
      social_account_ids: ids,
      platforms: platforms
    }))
  }, [selectedAccounts])

  const handleSelectAccount = (platform: string, accountId: number | null) => {
    setSelectedAccounts(prev => ({
      ...prev,
      [platform]: accountId
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Project Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Project Name *
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="My Template Project"
          required
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description
        </label>
        <input
          type="text"
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Optional description"
        />
      </div>

      {/* Workspace */}
      {workspaces && workspaces.length > 1 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Workspace
          </label>
          <select
            value={formData.workspace_id || ''}
            onChange={(e) => setFormData({ ...formData, workspace_id: Number(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {workspaces.map(ws => (
              <option key={ws.id} value={ws.id}>{ws.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Social Accounts */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Social Accounts
        </label>
        <p className="text-xs text-gray-500 mb-3">
          Select accounts for publishing. Platforms will be set automatically.
        </p>
        <div className="space-y-3">
          {['instagram', 'tiktok', 'youtube'].map(platform => {
            const platformAccounts = workspaceAccounts.filter(a => a.platform === platform && a.is_active)
            const selected = selectedAccounts[platform]

            return (
              <div key={platform} className="border rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">{platform}</span>
                </div>
                {platformAccounts.length === 0 ? (
                  <p className="text-xs text-gray-400 mt-1">No connected accounts</p>
                ) : (
                  <select
                    value={selected || ''}
                    onChange={(e) => handleSelectAccount(platform, e.target.value ? Number(e.target.value) : null)}
                    className="w-full mt-2 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">Not selected</option>
                    {platformAccounts.map(acc => (
                      <option key={acc.id} value={acc.id} disabled={acc.is_token_expired}>
                        {platform === 'youtube'
                          ? (acc.display_name || acc.username || acc.platform_user_id)
                          : `@${acc.username || acc.display_name || acc.platform_user_id}`}
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
      </div>

      {/* Aspect Ratio */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Aspect Ratio *
        </label>
        <select
          value={formData.image_aspect_ratio}
          onChange={(e) => setFormData({ ...formData, image_aspect_ratio: e.target.value as AspectRatio })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {ASPECT_RATIOS.map(ratio => (
            <option key={ratio.value} value={ratio.value}>{ratio.label}</option>
          ))}
        </select>
      </div>

      {/* Model Selection */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">AI Models</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              LLM Model
            </label>
            <select
              value={formData.llm_model}
              onChange={(e) => setFormData({ ...formData, llm_model: e.target.value as LLMModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {LLM_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Image Model
            </label>
            <select
              value={formData.image_model}
              onChange={(e) => setFormData({ ...formData, image_model: e.target.value as ImageModel })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {IMAGE_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Model
            </label>
            <select
              value={formData.video_model}
              onChange={(e) => {
                const newModel = e.target.value as VideoModel
                const newDuration = getDefaultDuration(newModel)
                setFormData({ ...formData, video_model: newModel, video_duration: newDuration })
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {VIDEO_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Duration
            </label>
            <select
              value={formData.video_duration}
              onChange={(e) => setFormData({ ...formData, video_duration: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {getDurationOptions(formData.video_model).map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Prompts */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Prompts</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preprocessing Prompt *
            </label>
            <textarea
              value={formData.preprocessing_prompt}
              onChange={(e) => setFormData({ ...formData, preprocessing_prompt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={4}
              placeholder="Given this data: {location}, {car}, {model}... Generate a creative scene description."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              LLM prompt for preprocessing variant data. Use {'{column_name}'} for CSV placeholders.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Image Prompt Template *
            </label>
            <textarea
              value={formData.image_prompt_template}
              onChange={(e) => setFormData({ ...formData, image_prompt_template: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={4}
              placeholder="A beautiful woman in {clothes} next to a {car} in {location}..."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Template for image generation prompt. Use {'{column_name}'} and {'{preprocessing_result}'}.
            </p>
          </div>
        </div>
      </div>

      {/* Video Template */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Default Video Template</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Template Name *
            </label>
            <input
              type="text"
              value={formData.video_template_name}
              onChange={(e) => setFormData({ ...formData, video_template_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Default"
              maxLength={100}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Prompt Template *
            </label>
            <textarea
              value={formData.video_template_prompt}
              onChange={(e) => setFormData({ ...formData, video_template_prompt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={3}
              placeholder="Camera slowly pans around the scene, cinematic motion..."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Template for video generation prompt.
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end space-x-4 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {isLoading ? 'Creating...' : 'Create Project'}
        </button>
      </div>
    </form>
  )
}
