export type WorkflowStatus =
  | 'pending'
  | 'in_progress'
  | 'validating'
  | 'validation_failed'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'completed'
  | 'failed'

export type StepType =
  | 'story'
  | 'description'
  | 'prompt'
  | 'image'
  | 'scenario'
  | 'video'
  | 'audio'
  | 'adaptation'
  | 'publishing'

export type ValidationStatus = 'pass' | 'pass_with_warnings' | 'fail'

export interface ValidationResult {
  id: number
  status: ValidationStatus
  score: number | null
  criteria_results: Record<string, any> | null
  warnings: string[] | null
  errors: string[] | null
  recommendations: string[] | null
  created_at: string
}

export interface PromptData {
  system_prompt: string
  user_prompt: string
  temperature?: number
}

export interface WorkflowStep {
  id: number
  video_id: number
  step_type: StepType
  status: WorkflowStatus
  content: Record<string, any> | null
  validation_attempts: number
  max_validation_attempts: number
  user_approved: boolean
  user_feedback: string | null
  prompt_used: string | null
  original_prompt: PromptData | null
  custom_prompt: PromptData | null
  prompt_manually_edited: boolean
  generation_time_seconds: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  validations: ValidationResult[]
}

export type AspectRatio = '9:16' | '16:9' | '1:1'
export type AudioMode = 'none' | 'scene' | 'music' | 'voiceover' | 'auto'
export type ProjectType = 'discover' | 'remix'

export interface SystemPrompts {
  story?: string
  description?: string
  prompt?: string
  scenario?: string
  adaptation?: string
}

export interface Project {
  id: number
  workspace_id: number
  name: string
  description: string | null
  story_template: string
  platforms: string[]
  duration: number
  aspect_ratio: AspectRatio
  audio_mode: AudioMode
  project_type: ProjectType
  require_image_approval: boolean
  system_prompts: SystemPrompts | null
  created_at: string
  updated_at: string
}

export interface CreateProjectDto {
  name: string
  description?: string
  story_template: string
  platforms: string[]
  duration: number
  aspect_ratio?: AspectRatio
  audio_mode?: AudioMode
  project_type?: ProjectType
  require_image_approval?: boolean
  system_prompts?: SystemPrompts
  workspace_id?: number
}

export interface UpdateProjectDto {
  name?: string
  description?: string
  story_template?: string
  platforms?: string[]
  duration?: number
  aspect_ratio?: AspectRatio
  audio_mode?: AudioMode
  project_type?: ProjectType
  require_image_approval?: boolean
  system_prompts?: SystemPrompts
}

export type WorkflowMode = 'MANUAL' | 'AUTO'

export interface Video {
  id: number
  project_id: number
  title: string
  workflow_mode: WorkflowMode
  content_variables: Record<string, any> | null
  story_data: Record<string, any> | null
  description_data: Record<string, any> | null
  prompt_data: Record<string, any> | null
  image_prompt: string | null
  image_url: string | null
  scenario_data: Record<string, any> | null
  video_url: string | null
  video_task_id: string | null
  audio_variants: string[] | null
  video_with_audio_url: string | null
  adaptation_data: Record<string, any> | null
  current_step: StepType
  status: WorkflowStatus
  author_rating: number | null
  created_at: string
  updated_at: string
  workflow_steps?: WorkflowStep[]
  project?: Project
  metrics?: VideoMetrics[]
}

export interface CreateVideoDto {
  project_id: number
  title: string
  workflow_mode?: WorkflowMode
  content_variables?: Record<string, any>
}

export interface UpdateVideoDto {
  title?: string
  workflow_mode?: WorkflowMode
  content_variables?: Record<string, any>
  story_data?: Record<string, any>
  description_data?: Record<string, any>
  image_prompt?: string
  image_url?: string
  scenario_data?: Record<string, any>
  video_url?: string
  adaptation_data?: Record<string, any>
  current_step?: StepType
  status?: WorkflowStatus
}

export interface ContentVariant {
  id: number
  description: string
  content_variables: {
    character?: Record<string, any>
    vehicle?: Record<string, any>
    location?: Record<string, any>
    [key: string]: Record<string, any> | undefined
  }
}

export interface GenerateVariantsResponse {
  variants: ContentVariant[]
}

export interface PublishResult {
  id: number
  platform: string
  status: string
  post_id: string | null
  post_url: string | null
  error_message: string | null
  published_at: string | null
  created_at: string
}

// --- Metrics Types ---

export type MetricsPeriod = '30m' | '6h' | '24h' | '7d'

export interface VideoMetrics {
  id: number
  video_id: number
  platform: string
  period: MetricsPeriod
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number | null
  recorded_at: string
  is_manual: boolean
}

export interface CreateVideoMetricsDto {
  platform: string
  period: MetricsPeriod
  views: number
  likes: number
  comments: number
  shares: number
}

export interface VideoMetricsSummary {
  video_id: number
  author_rating: number | null
  platforms: Record<string, Record<MetricsPeriod, VideoMetrics>>
  total_views: number
  total_likes: number
  total_comments: number
  total_shares: number
  avg_engagement_rate: number | null
}

// --- Invite & Workspace Types ---

export type InviteType = 'standalone' | 'workspace'

export interface Invite {
  id: number
  token: string
  type: InviteType
  email: string | null
  workspace_id: number | null
  workspace_name: string | null
  created_by_id: number
  created_at: string
  expires_at: string
  used_at: string | null
  used_by_id: number | null
  is_valid: boolean
}

export interface CreateInviteDto {
  type: InviteType
  email?: string
  workspace_id?: number
  expires_in_hours?: number
}

export interface InviteValidation {
  valid: boolean
  type?: InviteType
  email?: string
  workspace_name?: string
  expires_at?: string
  error?: string
}

export interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  role: string
  can_create_workspace: boolean
  created_at: string
}

export interface Workspace {
  id: number
  name: string
  owner_id: number
  created_at: string
  member_count?: number
  is_owner?: boolean
}

export interface WorkspaceMember {
  id: number
  workspace_id: number
  user_id: number
  role: string
  joined_at: string
  user?: User
}

export interface WorkspaceDetail {
  id: number
  name: string
  owner_id: number
  created_at: string
  members: WorkspaceMember[]
  is_owner: boolean
}

export interface CreateWorkspaceDto {
  name: string
}

// --- Workflow Data Types ---

export interface KeyMoment {
  timestamp: string
  action: string
  emotion?: string
}

export interface StoryData {
  concept: string
  hook: string
  emotional_arc: string
  key_moments: KeyMoment[]
  call_to_action?: string
  target_audience?: string
  platforms?: string[]
}

export interface DescriptionData {
  scene_description: string
  visual_style: string
  mood: string
  color_palette?: string[]
  key_elements?: string[]
  camera_suggestions?: string
}

export interface PromptResponseData {
  main_prompt: string
  negative_prompt?: string
  style_reference?: string
  composition_notes?: string
}

export interface CameraControl {
  type: string
  config?: Record<string, number>
}

export interface ScenarioData {
  motion_description: string
  camera_movement: string
  key_frames?: string[]
  duration_suggestion?: number
  camera_control?: CameraControl
}

export interface PlatformAdaptation {
  title?: string
  description?: string
  hashtags?: string[]
  caption?: string
  format?: string
  optimal_length?: number
  format_notes?: string
}

export interface AdaptationData {
  instagram?: PlatformAdaptation
  tiktok?: PlatformAdaptation
  youtube?: PlatformAdaptation
  [platform: string]: PlatformAdaptation | undefined
}

// --- API Error Type ---

export interface ApiError {
  message: string
  detail?: string
  status?: number
}

export function isApiError(error: unknown): error is { response?: { data?: { detail?: string } }; message?: string } {
  return typeof error === 'object' && error !== null
}

export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.response?.data?.detail || error.message || 'An error occurred'
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred'
}
