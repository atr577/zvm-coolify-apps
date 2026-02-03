import axios from 'axios'
import type { Project, CreateProjectDto, UpdateProjectDto, Video, CreateVideoDto, UpdateVideoDto, ContentVariant, GenerateVariantsResponse, VideoMetrics, CreateVideoMetricsDto, VideoMetricsSummary, MetricsPeriod, Invite, CreateInviteDto, InviteValidation, Workspace, WorkspaceDetail, CreateWorkspaceDto, PaginatedResponse, SocialAccount, TemplateSettings, TemplateSettingsUpdate, Variant, VariantListResponse, CSVUploadResponse, VariantUpdate, VideoTemplate, VideoTemplateCreate, VideoTemplateUpdate, GenerateRequest, Generation, GenerationListResponse, GenerationRatingUpdate } from '@/types'

const API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Projects API
export const projectsApi = {
  list: (page = 1, limit = 100) => api.get<PaginatedResponse<Project>>('/api/projects', { params: { page, limit } }),
  get: (id: number) => api.get<Project>(`/api/projects/${id}`),
  create: (data: CreateProjectDto) => api.post<Project>('/api/projects', data),
  update: (id: number, data: UpdateProjectDto) =>
    api.patch<Project>(`/api/projects/${id}`, data),
  delete: (id: number) => api.delete(`/api/projects/${id}`),
  bindSocialAccount: (projectId: number, accountId: number) =>
    api.post<Project>(`/api/projects/${projectId}/social-accounts`, { social_account_id: accountId }),
  unbindSocialAccount: (projectId: number, accountId: number) =>
    api.delete(`/api/projects/${projectId}/social-accounts/${accountId}`),
}

// Videos API
export const videosApi = {
  listByProject: (projectId: number, page = 1, limit = 100) =>
    api.get<PaginatedResponse<Video>>(`/api/videos/project/${projectId}`, { params: { page, limit } }),
  get: (id: number) => api.get<Video>(`/api/videos/${id}`),
  create: (data: CreateVideoDto) =>
    api.post<Video>('/api/videos', data),
  update: (id: number, data: UpdateVideoDto) =>
    api.patch<Video>(`/api/videos/${id}`, data),
  delete: (id: number) => api.delete(`/api/videos/${id}`),
}

// AI Generation API
export const aiApi = {
  generateVariants: (projectId: number) =>
    api.post<GenerateVariantsResponse>('/api/ai/generate-variants', { project_id: projectId }),

  regenerateVariants: (projectId: number, exclude: ContentVariant[]) =>
    api.post<GenerateVariantsResponse>('/api/ai/regenerate-variants', {
      project_id: projectId,
      exclude_variants: exclude
    }),
}

// Workflow step type
export type StepType = 'scenario' | 'image' | 'video' | 'audio'

// Workflow API responses
export interface GenerateStepResponse {
  variant_id: number
  step_type: StepType
  content: Record<string, unknown>
  is_selected: boolean
}

export interface VariantResponse {
  id: number
  step_type: StepType
  content: Record<string, unknown>
  is_selected: boolean
  created_at: string
}

export interface VariantsListResponse {
  step_type: StepType
  variants: VariantResponse[]
  selected_id: number | null
}

export interface SelectResponse {
  variant_id: number
  step_type: StepType
  stale_steps: StepType[]
}

export interface RunAutoResponse {
  video_id: number
  status: string
  completed_steps: StepType[]
  current_step: StepType | null
  error: string | null
}

// Custom prompt type for prompt editing
export interface CustomPrompt {
  system_prompt: string
  user_prompt: string
}

// Workflow API - 4-step pipeline: SCENARIO → IMAGE → VIDEO → AUDIO
export const workflowApi = {
  // Run all steps automatically (AUTO mode)
  runAuto: (videoId: number) =>
    api.post<RunAutoResponse>(`/api/workflow/${videoId}/run-auto`),

  // Generate a single step (MANUAL mode)
  generateStep: (videoId: number, step: StepType, feedback?: string, regenerate?: boolean) =>
    api.post<GenerateStepResponse>(`/api/workflow/${videoId}/generate/${step}`, { feedback, regenerate: regenerate ?? false }),

  // Get all variants for a step
  getVariants: (videoId: number, step: StepType) =>
    api.get<VariantsListResponse>(`/api/workflow/${videoId}/variants/${step}`),

  // Switch to a variant (for preview, no auto-continue)
  switchVariant: (videoId: number, variantId: number) =>
    api.post<{ variant_id: number; step_type: string; content: Record<string, unknown> }>(
      `/api/workflow/${videoId}/switch/${variantId}`
    ),

  // Approve variant and move to next step
  approveVariant: (videoId: number, variantId: number) =>
    api.post<SelectResponse>(`/api/workflow/${videoId}/approve/${variantId}`),

  // Legacy: kept for compatibility
  selectVariant: (videoId: number, variantId: number) =>
    api.post<SelectResponse>(`/api/workflow/${videoId}/select/${variantId}`),

  // Update step content (manual edit)
  updateContent: (videoId: number, step: StepType, content: Record<string, unknown>) =>
    api.patch<GenerateStepResponse>(`/api/workflow/${videoId}/update/${step}`, { content }),

  // Navigate to a specific step (MANUAL mode back navigation)
  gotoStep: (videoId: number, step: StepType) =>
    api.post<{ step: string; has_data: boolean }>(`/api/workflow/${videoId}/goto/${step}`),

  // Select a specific hook within an ai_music variant
  selectHook: (videoId: number, variantId: number, hookIndex: number) =>
    api.post<{ variant_id: number; selected_hook: number }>(
      `/api/workflow/${videoId}/variant/${variantId}/select-hook`,
      { hook_index: hookIndex }
    ),

  // Legacy: Generate publishing metadata (TODO: implement backend endpoint)
  generateMeta: (videoId: number) =>
    api.post<{ publishing_meta: Record<string, unknown> }>(`/api/videos/${videoId}/generate-meta`),

  // Legacy: Update publishing metadata (uses videos PATCH endpoint)
  updateMeta: (videoId: number, meta: Record<string, unknown>) =>
    api.patch(`/api/videos/${videoId}`, { publishing_meta: meta }),
}

// Re-export for backward compatibility
export type { SocialAccount } from '@/types'

export const socialAccountsApi = {
  list: () => api.get<SocialAccount[]>('/api/social-accounts'),
  getByPlatform: (platform: string) => api.get<SocialAccount[]>(`/api/social-accounts/platform/${platform}`),
  listByWorkspace: (workspaceId: number) => api.get<SocialAccount[]>(`/api/workspaces/${workspaceId}/social-accounts`),
}

export const publishingApi = {
  toYouTube: (videoId: number, socialAccountId: number, videoUrl: string, title: string, description: string, hashtags?: string, privacyStatus: string = 'public') =>
    api.post('/api/publish/youtube', {
      video_id: videoId,
      platform: 'youtube',
      video_url: videoUrl,
      title,
      description,
      hashtags,
      privacy_status: privacyStatus
    }, {
      params: { social_account_id: socialAccountId }
    }),

  toInstagram: (videoId: number, socialAccountId: number, videoUrl: string, title: string, description: string, hashtags?: string) =>
    api.post('/api/publish/instagram', {
      video_id: videoId,
      platform: 'instagram',
      video_url: videoUrl,
      title,
      description,
      hashtags
    }, {
      params: { social_account_id: socialAccountId }
    }),

  toTikTok: (videoId: number, socialAccountId: number, videoUrl: string, title: string, description: string, hashtags?: string) =>
    api.post('/api/publish/tiktok', {
      video_id: videoId,
      platform: 'tiktok',
      video_url: videoUrl,
      title,
      description,
      hashtags
    }, {
      params: { social_account_id: socialAccountId }
    }),

  getStatus: (videoId: number) =>
    api.get(`/api/publish/status/${videoId}`),

  retry: (publishResultId: number) =>
    api.post(`/api/publish/retry/${publishResultId}`),
}

// Invites API (admin only)
export const invitesApi = {
  list: () => api.get<Invite[]>('/api/auth/invites'),
  create: (data: CreateInviteDto) => api.post<Invite>('/api/auth/invites', data),
  delete: (id: number) => api.delete(`/api/auth/invites/${id}`),
  validate: (token: string) => api.get<InviteValidation>(`/api/auth/invite/${token}`),
}

// Workspaces API
export const workspacesApi = {
  list: () => api.get<Workspace[]>('/api/workspaces'),
  listAll: () => api.get<Workspace[]>('/api/workspaces/all'),  // Admin only
  get: (id: number) => api.get<WorkspaceDetail>(`/api/workspaces/${id}`),
  create: (data: CreateWorkspaceDto) => api.post<Workspace>('/api/workspaces', data),
  update: (id: number, data: CreateWorkspaceDto) => api.patch<Workspace>(`/api/workspaces/${id}`, data),
  delete: (id: number) => api.delete(`/api/workspaces/${id}`),
  removeMember: (workspaceId: number, userId: number) => api.delete(`/api/workspaces/${workspaceId}/members/${userId}`),
  // Workspace invites (owner only)
  listInvites: (workspaceId: number) => api.get<Invite[]>(`/api/workspaces/${workspaceId}/invites`),
  createInvite: (workspaceId: number, data: { email?: string; expires_in_hours?: number }) =>
    api.post<Invite>(`/api/workspaces/${workspaceId}/invites`, data),
  deleteInvite: (workspaceId: number, inviteId: number) =>
    api.delete(`/api/workspaces/${workspaceId}/invites/${inviteId}`),
}

// Metrics API
export const metricsApi = {
  // Add/update metrics for a video
  create: (videoId: number, data: CreateVideoMetricsDto) =>
    api.post<VideoMetrics>(`/api/metrics/video/${videoId}`, data),

  // Get all metrics for a video
  getByVideo: (videoId: number, platform?: string, period?: MetricsPeriod) =>
    api.get<VideoMetrics[]>(`/api/metrics/video/${videoId}`, {
      params: { platform, period }
    }),

  // Get aggregated summary
  getSummary: (videoId: number) =>
    api.get<VideoMetricsSummary>(`/api/metrics/video/${videoId}/summary`),

  // Update specific metrics entry
  update: (videoId: number, platform: string, period: MetricsPeriod, data: Partial<CreateVideoMetricsDto>) =>
    api.put<VideoMetrics>(`/api/metrics/video/${videoId}/${platform}/${period}`, data),

  // Delete metrics entry
  delete: (videoId: number, platform: string, period: MetricsPeriod) =>
    api.delete(`/api/metrics/video/${videoId}/${platform}/${period}`),

  // Set author rating (1-5)
  setRating: (videoId: number, rating: number) =>
    api.put(`/api/metrics/video/${videoId}/rating`, null, { params: { rating } }),

  // Get leaderboard
  getLeaderboard: (period: MetricsPeriod = '7d', sortBy: string = 'views', limit: number = 10) =>
    api.get<VideoMetricsSummary[]>('/api/metrics/leaderboard', {
      params: { period, sort_by: sortBy, limit }
    }),
}

// Template Project API
export const templateApi = {
  // Create template project
  createProject: (data: {
    name: string
    description?: string
    preprocessing_prompt: string
    image_prompt_template: string
    llm_model: string
    image_model: string
    video_model: string
    image_aspect_ratio: string
    video_template_name: string
    video_template_prompt: string
    duration?: number
    platforms?: string[]
    workspace_id?: number
  }) => api.post<{ id: number; name: string; project_type: string; message: string }>('/api/projects/template', data),

  // Template Settings
  getSettings: (projectId: number) =>
    api.get<TemplateSettings>(`/api/projects/${projectId}/template-settings`),

  updateSettings: (projectId: number, data: TemplateSettingsUpdate) =>
    api.put<TemplateSettings>(`/api/projects/${projectId}/template-settings`, data),

  // Variants
  uploadCsv: (projectId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<CSVUploadResponse>(`/api/projects/${projectId}/variants/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  listVariants: (projectId: number, params?: { search?: string; offset?: number; limit?: number }) =>
    api.get<VariantListResponse>(`/api/projects/${projectId}/variants`, { params }),

  updateVariant: (projectId: number, variantId: number, data: VariantUpdate) =>
    api.put<Variant>(`/api/projects/${projectId}/variants/${variantId}`, data),

  deleteVariant: (projectId: number, variantId: number) =>
    api.delete(`/api/projects/${projectId}/variants/${variantId}`),

  deleteAllVariants: (projectId: number) =>
    api.delete(`/api/projects/${projectId}/variants`),

  // Video Templates
  listVideoTemplates: (projectId: number, includeDeleted = false) =>
    api.get<VideoTemplate[]>(`/api/projects/${projectId}/video-templates`, {
      params: { include_deleted: includeDeleted }
    }),

  createVideoTemplate: (projectId: number, data: VideoTemplateCreate) =>
    api.post<VideoTemplate>(`/api/projects/${projectId}/video-templates`, data),

  getVideoTemplate: (projectId: number, templateId: number) =>
    api.get<VideoTemplate>(`/api/projects/${projectId}/video-templates/${templateId}`),

  updateVideoTemplate: (projectId: number, templateId: number, data: VideoTemplateUpdate) =>
    api.put<VideoTemplate>(`/api/projects/${projectId}/video-templates/${templateId}`, data),

  deleteVideoTemplate: (projectId: number, templateId: number) =>
    api.delete(`/api/projects/${projectId}/video-templates/${templateId}`),

  // Generations
  startGeneration: (projectId: number, data: GenerateRequest = {}) =>
    api.post<Generation>(`/api/projects/${projectId}/generate`, data),

  listGenerations: (projectId: number, params?: { offset?: number; limit?: number }) =>
    api.get<GenerationListResponse>(`/api/projects/${projectId}/generations`, { params }),

  getGeneration: (projectId: number, generationId: number) =>
    api.get<Generation>(`/api/projects/${projectId}/generations/${generationId}`),

  retryGeneration: (projectId: number, generationId: number) =>
    api.post<Generation>(`/api/projects/${projectId}/generations/${generationId}/retry`),

  deleteGeneration: (projectId: number, generationId: number) =>
    api.delete(`/api/projects/${projectId}/generations/${generationId}`),

  updateGenerationRating: (projectId: number, generationId: number, data: GenerationRatingUpdate) =>
    api.patch<Generation>(`/api/projects/${projectId}/generations/${generationId}/rating`, data),
}

// Moderation API (Template projects)
export const moderationApi = {
  // Get moderation queue (pending generations)
  getQueue: (projectId: number) =>
    api.get<ModerationQueueResponse>(`/api/projects/${projectId}/moderation-queue`),

  // Pre-generate publishing metadata without approving
  preGenerateMetadata: (projectId: number, generationId: number) =>
    api.post<PreGenerateMetadataResponse>(`/api/projects/${projectId}/moderation-queue/${generationId}/pre-generate-metadata`),

  // Approve generation (with optional pre-edited metadata)
  approve: (projectId: number, generationId: number, metadata?: Record<string, PlatformMetadata>) =>
    api.post<ApproveResponse>(
      `/api/projects/${projectId}/moderation-queue/${generationId}/approve`,
      metadata ? { publishing_metadata: metadata } : undefined
    ),

  // Reject generation (moves to archive)
  reject: (projectId: number, generationId: number, data: { reason: string; comment?: string }) =>
    api.post<RejectResponse>(`/api/projects/${projectId}/moderation-queue/${generationId}/reject`, data),

  // Regenerate (marks old as regenerated, starts new generation with optional feedback)
  regenerate: (projectId: number, generationId: number, data?: { feedback?: string }) =>
    api.post<RegenerateResponse>(`/api/projects/${projectId}/moderation-queue/${generationId}/regenerate`, data),

  // Get rejection archive
  getArchive: (projectId: number, params?: { offset?: number; limit?: number }) =>
    api.get<RejectionArchiveResponse>(`/api/projects/${projectId}/rejection-archive`, { params }),
}

// Moderation types
export interface PlatformMetadata {
  title: string
  description: string
  hashtags?: string
}

export interface PreGenerateMetadataResponse {
  metadata: Record<string, PlatformMetadata>
}

export interface ModerationQueueItem {
  id: number
  variant: { id: number; data: Record<string, unknown> } | null
  video_template: { id: number; name: string } | null
  preprocessing_result: Record<string, unknown> | null
  image_prompt: string | null
  video_prompt: string | null
  image_url: string | null
  video_url: string | null
  created_at: string
  completed_at: string | null
}

export interface ModerationQueueResponse {
  items: ModerationQueueItem[]
  total: number
}

export interface ApprovedGeneration {
  id: number
  project_id: number
  template_generation_id: number
  position: number
  approved_at: string
  publishing_metadata: Record<string, { title: string; description: string; hashtags?: string }> | null
  status: string
  platform_statuses: Record<string, string> | null
  retry_count: number
  last_error: string | null
  published_at: string | null
  created_at: string
  updated_at: string
  thumbnail_url: string | null
  video_url: string | null
}

export interface ApproveResponse {
  approved_generation: ApprovedGeneration
}

export interface Rejection {
  id: number
  project_id: number
  template_generation_id: number
  reason: string
  comment: string | null
  rejected_by: number | null
  rejected_at: string
  created_at: string
  thumbnail_url: string | null
}

export interface RejectResponse {
  rejection: Rejection
}

export interface RegenerateResponse {
  new_generation: {
    id: number
    status: string
    variant_id: number | null
    video_template_id: number | null
    created_at: string | null
  }
}

export interface RejectionArchiveItem {
  id: number
  template_generation_id: number
  reason: string
  comment: string | null
  rejected_by: number | null
  rejected_by_name: string | null
  rejected_at: string
  thumbnail_url: string | null
  variant_data: Record<string, unknown> | null
}

export interface RejectionArchiveResponse {
  items: RejectionArchiveItem[]
  total: number
}

// --- Publishing Schedule API (T21) ---

export interface PublishingConfig {
  id: number
  project_id: number
  enabled: boolean
  is_paused: boolean
  days: string[]
  preferred_times: string[]
  depth_days: number
  created_at: string | null
  updated_at: string | null
}

export interface PublishingConfigUpdate {
  enabled: boolean
  is_paused: boolean
  days: string[]
  preferred_times: string[]
  depth_days: number
}

export interface PipelineStats {
  generating_count: number
  review_count: number
  approved_count: number
  scheduled_count: number
  total_schedule_slots: number
  variants_count: number
  templates_count: number
}

export interface PublishingQueueItem {
  id: number
  project_id: number
  template_generation_id: number
  position: number
  approved_at: string
  publishing_metadata: Record<string, { title: string; description: string; hashtags: string }> | null
  status: string
  platform_statuses: Record<string, string> | null
  retry_count: number
  last_error: string | null
  published_at: string | null
  created_at: string | null
  updated_at: string | null
  thumbnail_url: string | null
  video_url: string | null
}

export interface PublishingQueueResponse {
  items: PublishingQueueItem[]
  total: number
}

export interface ScheduleSlotItem {
  id: number
  generation_id: number
  thumbnail_url: string | null
  video_url: string | null
  publishing_metadata: Record<string, { title: string; description: string; hashtags: string }> | null
  status: string
  platform_statuses: Record<string, string> | null
}

export interface ScheduleSlot {
  scheduled_at: string
  item: ScheduleSlotItem | null
}

export interface ScheduleWarning {
  type: 'queue_low' | 'no_platforms' | 'config_disabled'
  message: string
}

export interface PublishingScheduleResponse {
  config: {
    enabled: boolean
    is_paused: boolean
    days: string[]
    preferred_times: string[]
    timezone: string
    depth_days: number
  }
  slots: ScheduleSlot[]
  warnings: ScheduleWarning[]
}

export const publishingScheduleApi = {
  // Get publishing config
  getConfig: (projectId: number) =>
    api.get<PublishingConfig>(`/api/projects/${projectId}/publishing-config`),

  // Update publishing config
  updateConfig: (projectId: number, data: PublishingConfigUpdate) =>
    api.put<PublishingConfig>(`/api/projects/${projectId}/publishing-config`, data),

  // Get publishing queue
  getQueue: (projectId: number) =>
    api.get<PublishingQueueResponse>(`/api/projects/${projectId}/publishing-queue`),

  // Update queue item metadata
  updateQueueItem: (projectId: number, itemId: number, data: { publishing_metadata: Record<string, { title: string; description: string; hashtags: string }> }) =>
    api.put<PublishingQueueItem>(`/api/projects/${projectId}/publishing-queue/${itemId}`, data),

  // Delete queue item
  deleteQueueItem: (projectId: number, itemId: number) =>
    api.delete(`/api/projects/${projectId}/publishing-queue/${itemId}`),

  // Get computed schedule
  getSchedule: (projectId: number) =>
    api.get<PublishingScheduleResponse>(`/api/projects/${projectId}/publishing-schedule`),

  // Get pipeline funnel stats
  getPipelineStats: (projectId: number) =>
    api.get<PipelineStats>(`/api/projects/${projectId}/pipeline-stats`),
}

export default api
