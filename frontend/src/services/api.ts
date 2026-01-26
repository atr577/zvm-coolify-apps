import axios from 'axios'
import type { Project, CreateProjectDto, UpdateProjectDto, Video, CreateVideoDto, UpdateVideoDto, ContentVariant, GenerateVariantsResponse, VideoMetrics, CreateVideoMetricsDto, VideoMetricsSummary, MetricsPeriod, Invite, CreateInviteDto, InviteValidation, Workspace, WorkspaceDetail, CreateWorkspaceDto, PaginatedResponse } from '@/types'

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

export interface SocialAccount {
  id: number
  platform: string
  platform_user_id: string
  username?: string
  display_name?: string
  profile_picture?: string
  is_active: boolean
}

export const socialAccountsApi = {
  list: () => api.get<SocialAccount[]>('/api/social-accounts'),
  getByPlatform: (platform: string) => api.get<SocialAccount[]>(`/api/social-accounts/platform/${platform}`),
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

export default api
