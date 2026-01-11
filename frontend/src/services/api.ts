import axios from 'axios'
import type { Project, CreateProjectDto, UpdateProjectDto, Video, CreateVideoDto, UpdateVideoDto, ContentVariant, GenerateVariantsResponse, VideoMetrics, CreateVideoMetricsDto, VideoMetricsSummary, MetricsPeriod, Invite, CreateInviteDto, InviteValidation, Workspace, WorkspaceDetail, CreateWorkspaceDto, PaginatedResponse } from '@/types'

// Flexible types for workflow data from API (may have additional/missing fields)
type WorkflowData = Record<string, unknown>

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

export interface StoryParams {
  theme?: string
  target_audience?: string
  mood?: string
  key_elements?: string
  duration: number
  platforms?: string[]
  additional_notes?: string
  custom_prompt?: {
    system_prompt: string
    user_prompt: string
  }
}

export interface CustomPrompt {
  system_prompt: string
  user_prompt: string
}

export interface PreviewPromptRequest {
  video_id: number
  step_type: 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'
  context?: Record<string, unknown>
}

export interface PreviewPromptResponse {
  system_prompt: string
  user_prompt: string
  step_type: string
  can_edit: boolean
}

// Workflow API (обновленный для video_id)
export const workflowApi = {
  // Preview prompt before generation
  previewPrompt: (request: PreviewPromptRequest) =>
    api.post<PreviewPromptResponse>('/api/workflow/preview-prompt', request),

  generateStory: (videoId: number, params: StoryParams) =>
    api.post('/api/workflow/generate-story', {
      video_id: videoId,
      ...params
    }),

  generateDescription: (videoId: number, storyData: WorkflowData, customPrompt?: CustomPrompt) =>
    api.post('/api/workflow/generate-description', {
      video_id: videoId,
      story_data: storyData,
      custom_prompt: customPrompt
    }),

  generatePrompt: (videoId: number, descriptionData: WorkflowData, customPrompt?: CustomPrompt) =>
    api.post('/api/workflow/generate-prompt', {
      video_id: videoId,
      description_data: descriptionData,
      custom_prompt: customPrompt
    }),

  generateImage: (videoId: number, promptOrData: string | WorkflowData, aspectRatio = '9:16', mode = 'std', refillFromTemplate = false) =>
    api.post('/api/workflow/generate-image', {
      video_id: videoId,
      ...(typeof promptOrData === 'string'
        ? { prompt: promptOrData }
        : { prompt_data: promptOrData, prompt: (promptOrData as { main_prompt?: string }).main_prompt }
      ),
      aspect_ratio: aspectRatio,
      mode,
      refill_from_template: refillFromTemplate
    }),

  generateScenario: (videoId: number, imageUrl: string, descriptionData: WorkflowData, customPrompt?: CustomPrompt) =>
    api.post('/api/workflow/generate-scenario', {
      video_id: videoId,
      image_url: imageUrl,
      description_data: descriptionData,
      custom_prompt: customPrompt
    }),

  generateVideo: (videoId: number, imageUrl: string, scenarioData: WorkflowData, duration = 5, mode = 'std') =>
    api.post('/api/workflow/generate-video', {
      video_id: videoId,
      image_url: imageUrl,
      scenario_data: scenarioData,
      duration,
      mode,
      version: '2.5'
    }),

  generateAudio: (videoId: number) =>
    api.post('/api/workflow/generate-audio', { video_id: videoId }),

  selectAudioVariant: (videoId: number, variantIndex: number) =>
    api.post('/api/workflow/select-audio-variant', {
      video_id: videoId,
      variant_index: variantIndex
    }),

  adaptForPlatforms: (videoId: number, scenarioData: WorkflowData, platforms: string[], customPrompt?: CustomPrompt) =>
    api.post('/api/workflow/adapt-for-platforms', {
      video_id: videoId,
      scenario_data: scenarioData,
      platforms,
      custom_prompt: customPrompt
    }),

  generateMeta: (videoId: number) =>
    api.post(`/api/workflow/generate-meta?video_id=${videoId}`),

  updateMeta: (videoId: number, meta: Record<string, { title: string; description: string; hashtags: string }>) =>
    api.patch(`/api/workflow/update-meta?video_id=${videoId}`, meta),

  approveStep: (stepId: number, approved: boolean, feedback?: string, regenerate: boolean = true) =>
    api.post('/api/workflow/approve-step', {
      step_id: stepId,
      approved,
      feedback,
      regenerate: !approved ? regenerate : false
    }),

  autoGenerateToVideo: (videoId: number) =>
    api.post('/api/workflow/auto-generate-to-video', { video_id: videoId }),

  // New v2 API endpoints (per CONTRACTS.md)
  startWorkflow: (videoId: number) =>
    api.post(`/api/workflow/${videoId}/start`),

  getVariants: (videoId: number, stepType: string) =>
    api.get(`/api/workflow/${videoId}/${stepType}/variants`),

  selectVariant: (videoId: number, stepType: string, variantId: number) =>
    api.post(`/api/workflow/${videoId}/${stepType}/select`, { variant_id: variantId }),

  approveStepV2: (videoId: number, stepType: string) =>
    api.post(`/api/workflow/${videoId}/${stepType}/approve`),

  rejectStep: (videoId: number, stepType: string, reason?: string) =>
    api.post(`/api/workflow/${videoId}/${stepType}/reject`, { reason }),

  regenerateStep: (videoId: number, stepType: string, variantId: number, feedback?: string) =>
    api.post(`/api/workflow/${videoId}/${stepType}/regenerate`, { variant_id: variantId, feedback }),

  retryStep: (videoId: number, stepType: string) =>
    api.post(`/api/workflow/${videoId}/${stepType}/retry`),

  rollbackToStep: (videoId: number, targetStep: string) =>
    api.post(`/api/workflow/${videoId}/rollback/${targetStep}`),
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
