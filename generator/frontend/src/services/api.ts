import axios from 'axios'
import type { Project, CreateProjectDto, UpdateProjectDto, Video, CreateVideoDto, UpdateVideoDto, ContentVariant, GenerateVariantsResponse } from '@/types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Projects API
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects'),
  get: (id: number) => api.get<Project>(`/api/projects/${id}`),
  create: (data: CreateProjectDto) => api.post<Project>('/api/projects', data),
  update: (id: number, data: UpdateProjectDto) =>
    api.patch<Project>(`/api/projects/${id}`, data),
  delete: (id: number) => api.delete(`/api/projects/${id}`),
}

// Videos API
export const videosApi = {
  listByProject: (projectId: number) =>
    api.get<Video[]>(`/api/videos/project/${projectId}`),
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
}

// Workflow API (обновленный для video_id)
export const workflowApi = {
  generateStory: (videoId: number, params: StoryParams) =>
    api.post('/api/workflow/generate-story', {
      video_id: videoId,
      ...params
    }),

  generateDescription: (videoId: number, storyData: any) =>
    api.post('/api/workflow/generate-description', { video_id: videoId, story_data: storyData }),

  generatePrompt: (videoId: number, descriptionData: any) =>
    api.post('/api/workflow/generate-prompt', { video_id: videoId, description_data: descriptionData }),

  generateImage: (videoId: number, promptOrData: string | any, aspectRatio = '9:16', mode = 'std') =>
    api.post('/api/workflow/generate-image', {
      video_id: videoId,
      ...(typeof promptOrData === 'string'
        ? { prompt: promptOrData }
        : { prompt_data: promptOrData, prompt: promptOrData.main_prompt }
      ),
      aspect_ratio: aspectRatio,
      mode
    }),

  generateScenario: (videoId: number, imageUrl: string, descriptionData: any) =>
    api.post('/api/workflow/generate-scenario', {
      video_id: videoId,
      image_url: imageUrl,
      description_data: descriptionData
    }),

  generateVideo: (videoId: number, imageUrl: string, scenarioData: any, duration = 5, mode = 'std') =>
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

  adaptForPlatforms: (videoId: number, scenarioData: any, platforms: string[]) =>
    api.post('/api/workflow/adapt-for-platforms', {
      video_id: videoId,
      scenario_data: scenarioData,
      platforms
    }),

  approveStep: (stepId: number, approved: boolean, feedback?: string, regenerate: boolean = true) =>
    api.post('/api/workflow/approve-step', {
      step_id: stepId,
      approved,
      feedback,
      regenerate: !approved ? regenerate : false
    }),

  autoGenerateToVideo: (videoId: number) =>
    api.post('/api/workflow/auto-generate-to-video', { video_id: videoId }),
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

export default api
