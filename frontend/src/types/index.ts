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

export type StepType = 'scenario' | 'image' | 'video' | 'audio'

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


export type AspectRatio = '9:16' | '16:9' | '1:1'
export type AudioMode = 'none' | 'scene' | 'music' | 'voiceover' | 'auto'
export type AudioProvider = 'kling' | 'ai_music'
export type ProjectType = 'discover' | 'remix' | 'template'

export interface SystemPrompts {
  story?: string
  description?: string
  prompt?: string
  scenario?: string
  adaptation?: string
}

export interface SocialAccount {
  id: number
  platform: string
  platform_user_id: string
  username: string | null
  display_name: string | null
  profile_picture: string | null
  is_active: boolean
  created_at: string
  is_token_expired: boolean
}

export interface Project {
  id: number
  workspace_id: number
  name: string
  description: string | null
  story_template: string
  motion_template: string | null  // Motion prompt template (for remix)
  platforms: string[]
  social_accounts: SocialAccount[]
  duration: number
  aspect_ratio: AspectRatio
  audio_mode: AudioMode
  audio_provider: AudioProvider | null  // null = use default for audio_mode
  project_type: ProjectType
  require_image_approval: boolean
  system_prompts: SystemPrompts | null
  timezone: string  // IANA timezone for scheduled publishing
  // Remix-specific fields
  source_video_ids: number[] | null
  scenario_template: Record<string, string> | null
  placeholders: string[] | null
  placeholder_suggestions: Record<string, string[]> | null
  created_at: string
  updated_at: string
}

export interface CreateProjectDto {
  name: string
  description?: string
  story_template: string
  motion_template?: string  // Motion prompt template (for remix)
  platforms: string[]
  duration: number
  aspect_ratio?: AspectRatio
  audio_mode?: AudioMode
  audio_provider?: AudioProvider  // null = use default for audio_mode
  project_type?: ProjectType
  require_image_approval?: boolean
  system_prompts?: SystemPrompts
  workspace_id?: number
  // Remix-specific fields
  source_video_ids?: number[]
  scenario_template?: Record<string, string>
  placeholders?: string[]
  placeholder_suggestions?: Record<string, string[]>
}

export interface UpdateProjectDto {
  name?: string
  description?: string
  story_template?: string
  motion_template?: string  // Motion prompt template (for remix)
  platforms?: string[]
  duration?: number
  aspect_ratio?: AspectRatio
  audio_mode?: AudioMode
  audio_provider?: AudioProvider  // null = use default for audio_mode
  project_type?: ProjectType
  require_image_approval?: boolean
  system_prompts?: SystemPrompts
  timezone?: string
  workspace_id?: number
  // Remix-specific fields
  source_video_ids?: number[]
  scenario_template?: Record<string, string>
  placeholders?: string[]
  placeholder_suggestions?: Record<string, string[]>
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
  audio_data: Record<string, any> | null  // ai_music step result
  audio_variants: string[] | null  // deprecated
  video_with_audio_url: string | null
  // Local file paths (served via /api/files)
  local_image_path: string | null
  local_video_path: string | null
  local_audio_path: string | null
  adaptation_data: Record<string, any> | null
  publishing_meta: Record<string, any> | null
  current_step: StepType
  status: WorkflowStatus
  author_rating: number | null
  is_published: boolean
  published_at: string | null
  created_at: string
  updated_at: string
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
  video_id: number | null
  approved_generation_id: number | null
  platform: string
  period: MetricsPeriod
  views: number
  likes: number
  comments: number
  shares: number
  saves: number
  reach: number
  avg_watch_time_ms: number | null
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

// --- Project Analytics Types (T42) ---

export type MetricsStatus = 'complete' | 'pending' | 'not_collected' | 'no_post_id'

export interface GenerationPlatformMetrics {
  post_id: string | null
  post_url: string | null
  period: string
  views: number
  likes: number
  comments: number
  shares: number
  saves: number
  reach: number
  engagement_rate: number | null
  virality_rate: number | null
  save_rate: number | null
}

export interface GenerationMetrics {
  approved_generation_id: number
  template_generation_id: number
  thumbnail_url: string | null
  published_at: string | null
  platforms: Record<string, GenerationPlatformMetrics>
  metrics_status: MetricsStatus
}

export interface ProjectMetricsTotals {
  total_published: number
  total_views: number
  avg_engagement_rate: number | null
  avg_virality_rate: number | null
}

export interface ProjectMetricsResponse {
  generations: GenerationMetrics[]
  totals: ProjectMetricsTotals
}

// --- Dashboard Analytics Summary (T48) ---

export interface DashboardProjectSummary {
  project_id: number
  project_name: string
  published_count: number
  total_views: number
  avg_views_per_video: number
  best_video_views: number
  last_published_at: string | null
}

export interface DashboardProjectHealth {
  project_id: number
  project_name: string
  queue_size: number
  daily_publish_rate: number
  queue_days: number | null
  health_status: 'green' | 'yellow' | 'red'
  health_note: string | null
  pending_moderation: number
  actual_cadence_last_7d: number
  target_cadence: number
}

export interface DashboardSummaryResponse {
  total_published: number
  total_views: number
  avg_views_per_video: number
  publishing_cadence_actual: number
  publishing_cadence_target: number
  projects: DashboardProjectSummary[]
  health: DashboardProjectHealth[]
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


// --- Template Project Types ---

export type LLMModel = 'gpt-4o-mini' | 'gpt-4o'
export type ImageModel = 'fal-ai/nano-banana-pro' | 'fal-ai/flux-pro/v1.1-ultra' | 'fal-ai/flux-pro/v1.1' | 'fal-ai/ideogram/v3' | 'fal-ai/imagen3'
export type VideoModel = 'fal-ai/veo3/fast/image-to-video' | 'fal-ai/veo3/image-to-video' | 'fal-ai/veo3.1/reference-to-video' | 'fal-ai/kling-video/v2.1/standard/image-to-video' | 'fal-ai/kling-video/v2.1/pro/image-to-video' | 'fal-ai/kling-video/v3/standard/image-to-video' | 'fal-ai/kling-video/v3/pro/image-to-video' | 'fal-ai/minimax/video-01'
export type GenerationStatus = 'pending' | 'preprocessing' | 'generating_image' | 'generating_video' | 'generating_audio' | 'merging_audio' | 'completed' | 'failed' | 'cancelled'

export interface TemplateSettings {
  id: number
  project_id: number
  preprocessing_prompt: string
  image_prompt_template: string
  llm_model: string
  image_model: string
  video_model: string
  image_aspect_ratio: string
  video_duration: string
  variant_generation_prompt: string | null
  music_mode: string | null
  music_prompt: string | null
  meta_title_prompt: string | null
  meta_description_prompt: string | null
  meta_hashtags_prompt: string | null
  audio_hook_url: string | null
  audio_hook_duration_ms: number | null
  audio_hook_retrim: boolean
  csv_columns: string[] | null
  reference_video_url: string | null
  created_at: string
  updated_at: string
}

export interface TemplateSettingsUpdate {
  preprocessing_prompt?: string
  image_prompt_template?: string
  llm_model?: LLMModel
  image_model?: ImageModel
  video_model?: VideoModel
  image_aspect_ratio?: AspectRatio
  video_duration?: string
  variant_generation_prompt?: string
  music_mode?: string
  music_prompt?: string
  meta_title_prompt?: string
  meta_description_prompt?: string
  meta_hashtags_prompt?: string
}

export interface Variant {
  id: number
  project_id: number
  row_number: number
  data: Record<string, string>
  usage_count: number
  last_used_at: string | null
  created_at: string
}

export interface VariantListResponse {
  variants: Variant[]
  total: number
  csv_columns: string[] | null
}

export interface CSVUploadResponse {
  variants_created: number
  csv_columns: string[]
  preview: Record<string, string>[]
}

export interface VariantUpdate {
  data?: Record<string, string>
}

export interface VideoTemplate {
  id: number
  project_id: number
  name: string
  prompt: string
  is_default: boolean
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface VideoTemplateCreate {
  name: string
  prompt: string
  is_default?: boolean
}

export interface VideoTemplateUpdate {
  name?: string
  prompt?: string
  is_default?: boolean
}

export interface GenerateRequest {
  variant_id?: number
  video_template_id?: number
}

export interface Generation {
  id: number
  project_id: number
  variant_id: number | null
  video_template_id: number | null
  llm_model: string
  image_model: string
  video_model: string
  preprocessing_result: Record<string, unknown> | null
  image_prompt: string | null
  video_prompt: string | null
  image_url: string | null
  video_url: string | null
  image_path: string | null
  video_path: string | null
  audio_path: string | null
  video_with_audio_path: string | null
  status: GenerationStatus
  failed_at_step: string | null
  error_message: string | null
  variant_data: Record<string, string> | null
  moderation_status: 'approved' | 'rejected' | 'regenerated' | null
  batch_id: string | null
  created_at: string
  completed_at: string | null
}

export interface GenerationListResponse {
  generations: Generation[]
  total: number
}

export type BatchMode = 'all_unused' | 'least_used' | 'specific'

export interface BatchGenerateRequest {
  mode: BatchMode
  count?: number
  variant_ids?: number[]
  video_template_id?: number
}

export interface BatchGenerateResponse {
  batch_id: string
  count: number
  generations: Generation[]
}

// --- Discover Workflow ---

export type DiscoverStage = 'images' | 'videos' | 'audio' | 'extraction' | 'completed'
export type DiscoverStatus = 'active' | 'completed' | 'archived'
export type DiscoverRoundType = 'image' | 'video'
export type DiscoverRoundStatus = 'pending' | 'generating' | 'completed' | 'failed'
export type DiscoverItemStatus = 'pending' | 'generating' | 'completed' | 'failed'
export type DiscoverSelection = 'unreviewed' | 'selected' | 'rejected'

export interface DiscoverItem {
  id: number
  position: number
  prompt: string
  source_image_item_id: number | null
  status: DiscoverItemStatus
  result_url: string | null
  local_path: string | null
  error_message: string | null
  selection: DiscoverSelection
  created_at: string
  completed_at: string | null
}

export interface DiscoverRound {
  id: number
  round_number: number
  round_type: DiscoverRoundType
  status: DiscoverRoundStatus
  error_message: string | null
  feedback_text: string | null
  model_used: string | null
  total_items: number
  selected_count: number
  rejected_count: number
  items: DiscoverItem[]
  created_at: string
  completed_at: string | null
}

export interface DiscoverExtraction {
  id: number
  winning_image_prompt: string
  winning_video_prompt: string | null
  base_prompt: string
  variation_prompt: string
  slot_names: string[] | null
  slot_examples: Record<string, string[]> | null
  edited_base_prompt: string | null
  edited_variation_prompt: string | null
  created_at: string
  updated_at: string
}

export type AudioType = 'sfx' | 'music' | 'library'

export interface AudioHook {
  start_ms: number
  end_ms: number
  energy: string
  type: string
}

export interface DiscoverAudioVariant {
  id: number
  audio_type: AudioType
  prompt: string | null
  prompt_mode: 'manual' | 'auto'
  status: 'pending' | 'generating' | 'completed' | 'failed'
  file_url: string | null
  trimmed_file_url: string | null
  full_duration_ms: number | null
  duration_ms: number | null
  detected_hooks: AudioHook[] | null
  hook_start_ms: number | null
  hook_end_ms: number | null
  error_message: string | null
  library_item_id: number | null
  created_at: string
}

export interface AudioLibraryItem {
  id: number
  source_type: 'sfx' | 'music'
  duration_ms: number
  file_url: string | null
  prompt: string | null
  mood: string | null
  use_count: number
  created_at: string
}

export interface AudioLibrarySearchResponse {
  items: AudioLibraryItem[]
  total: number
  page: number
  page_size: number
}

export interface DiscoverProject {
  id: number
  concept: string
  name: string
  stage: DiscoverStage
  status: DiscoverStatus
  current_image_round: number
  current_video_round: number
  image_model: string
  video_model: string
  image_aspect_ratio: string
  video_duration: string
  finalist_image_item_id: number | null
  finalist_video_item_id: number | null
  audio_mode: string | null
  selected_audio_variant_id: number | null
  merged_video_url: string | null
  audio_variants: DiscoverAudioVariant[]
  created_project_id: number | null
  rounds: DiscoverRound[]
  extraction: DiscoverExtraction | null
  created_at: string
  updated_at: string
}

export interface DiscoverProjectListResponse {
  projects: DiscoverProject[]
  total: number
}

export interface DiscoverProjectCreate {
  concept: string
  name: string
  workspace_id: number
  image_model?: string
  video_model?: string
  image_aspect_ratio?: string
  video_duration?: string
}

export interface DiscoverSelectionRequest {
  selections: Record<string, 'selected' | 'rejected'>
  feedback?: string
}

export interface DiscoverSelectionResponse {
  round_id: number
  selected_count: number
  rejected_count: number
  can_advance_to_video: boolean
  can_generate_next_round: boolean
}

export interface DiscoverCreateTemplateRequest {
  name: string
  platforms?: string[]
  video_template_prompt: string
}

// --- Refinement ---

export type BlockStatus = 'auto_filled' | 'needs_input' | 'auto_generated' | 'confirmed'

export interface DiscoverRefinementBlock {
  value: string | null
  status: BlockStatus
  source: 'parsed' | 'llm' | 'user' | 'settings' | null
  question?: string | null
  options?: string[] | null
}

export interface DiscoverRefinement {
  refinement_id: number
  original_concept: string
  score: number
  relevant_blocks: string[]
  blocks: Record<string, DiscoverRefinementBlock>
  refined_prompt: string | null
  ready_to_generate: boolean
}

// --- API Error Type ---

export interface ApiError {
  message: string
  detail?: string
  status?: number
}

// --- Pagination ---

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages?: number
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
