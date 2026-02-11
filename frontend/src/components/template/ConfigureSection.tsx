import { useState, useEffect, useCallback, useMemo } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import {
  templateApi,
  projectsApi,
  workspacesApi,
  socialAccountsApi,
  publishingScheduleApi,
} from '@/services/api'
import type {
  SocialAccount,
  TemplateSettings,
  Workspace,
  LLMModel,
  ImageModel,
  VideoModel,
  AspectRatio,
} from '@/types'
import { getDefaultDuration } from '@/constants/models'
import { StickySaveBar } from './StickySaveBar'
import { InputStep } from './InputStep'
import { PreprocessingStep } from './PreprocessingStep'
import { ImageStep } from './ImageStep'
import { VideoStep } from './VideoStep'
import { DistributionStep } from './DistributionStep'

interface ConfigureSectionProps {
  projectId: number
  showProjectSettings?: boolean
}

// Settings that can be edited (preprocessing, image, video, music fields)
interface EditableSettings {
  llm_model: string
  preprocessing_prompt: string
  image_model: string
  image_aspect_ratio: string
  image_prompt_template: string
  video_model: string
  video_duration: string
  variant_generation_prompt: string
  music_mode: string
  music_prompt: string
}

// Publishing config editable fields
interface EditablePublishing {
  is_paused: boolean
  days: string[]
  preferred_times: string[]
  depth_days: number
}

// Project info editable fields
interface EditableProjectInfo {
  name: string
  description: string
  workspace_id: number | undefined
}

type StepNumber = 1 | 2 | 3 | 4 | 5 | 6

type StepStatus = 'complete' | 'incomplete' | 'empty'

export function ConfigureSection({ projectId, showProjectSettings }: ConfigureSectionProps) {
  const [activeStep, setActiveStep] = useState<StepNumber | null>(null)

  // Loading
  const [loading, setLoading] = useState(true)

  // Template settings (from API)
  const [settings, setSettings] = useState<TemplateSettings | null>(null)
  const [initialSettings, setInitialSettings] = useState<EditableSettings | null>(null)
  const [editedSettings, setEditedSettings] = useState<EditableSettings | null>(null)

  // Publishing config
  const [initialPublishing, setInitialPublishing] = useState<EditablePublishing | null>(null)
  const [editedPublishing, setEditedPublishing] = useState<EditablePublishing | null>(null)

  // Counts
  const [variantsCount, setVariantsCount] = useState(0)
  const [templatesCount, setTemplatesCount] = useState(0)

  // Social accounts
  const [boundAccounts, setBoundAccounts] = useState<SocialAccount[]>([])
  const [workspaceAccounts, setWorkspaceAccounts] = useState<SocialAccount[]>([])
  const [workspaceId, setWorkspaceId] = useState<number | null>(null)
  const [timezone, setTimezone] = useState('UTC')
  const [initialTimezone, setInitialTimezone] = useState('UTC')
  const [bindingLoading, setBindingLoading] = useState<string | null>(null)

  // Audio hook preview URL (re-trimmed for current video_duration)
  const [hookPreviewUrl, setHookPreviewUrl] = useState<string | null>(null)

  // Project info (for Details tab)
  const [initialProjectInfo, setInitialProjectInfo] = useState<EditableProjectInfo | null>(null)
  const [editedProjectInfo, setEditedProjectInfo] = useState<EditableProjectInfo | null>(null)
  const [allWorkspaces, setAllWorkspaces] = useState<Workspace[]>([])

  // Fetch re-trimmed hook preview as blob when duration changes
  useEffect(() => {
    if (
      settings?.audio_hook_retrim &&
      editedSettings?.music_mode === 'library' &&
      editedSettings?.video_duration
    ) {
      let cancelled = false
      const token = localStorage.getItem('auth_token')
      fetch(`/api/projects/${projectId}/audio-hook-preview?duration=${editedSettings.video_duration}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
        .then(res => {
          if (!res.ok) throw new Error(`${res.status}`)
          return res.blob()
        })
        .then(blob => {
          if (!cancelled) {
            const url = URL.createObjectURL(blob)
            setHookPreviewUrl(prev => {
              if (prev) URL.revokeObjectURL(prev)
              return url
            })
          }
        })
        .catch(() => {
          if (!cancelled) setHookPreviewUrl(null)
        })
      return () => { cancelled = true }
    } else {
      setHookPreviewUrl(prev => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
    }
  }, [settings?.audio_hook_retrim, editedSettings?.video_duration, editedSettings?.music_mode, projectId])

  // Refresh triggers for child components
  const [variantsRefresh, setVariantsRefresh] = useState(0)

  // Load all data
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [settingsRes, projectRes, variantsRes, templatesRes, pubConfigRes] =
        await Promise.all([
          templateApi.getSettings(projectId),
          projectsApi.get(projectId),
          templateApi.listVariants(projectId, { limit: 1 }),
          templateApi.listVideoTemplates(projectId),
          publishingScheduleApi.getConfig(projectId),
        ])

      const s = settingsRes.data
      setSettings(s)
      const editable: EditableSettings = {
        llm_model: s.llm_model,
        preprocessing_prompt: s.preprocessing_prompt,
        image_model: s.image_model,
        image_aspect_ratio: s.image_aspect_ratio,
        image_prompt_template: s.image_prompt_template,
        video_model: s.video_model,
        video_duration: s.video_duration,
        variant_generation_prompt: s.variant_generation_prompt || '',
        music_mode: s.music_mode || 'none',
        music_prompt: s.music_prompt || '',
      }
      setInitialSettings(editable)
      setEditedSettings({ ...editable })

      const project = projectRes.data
      setBoundAccounts(project.social_accounts || [])
      setWorkspaceId(project.workspace_id)
      const tz = project.timezone || 'UTC'
      setTimezone(tz)
      setInitialTimezone(tz)

      // Project info for Details tab
      const projInfo: EditableProjectInfo = {
        name: project.name,
        description: project.description || '',
        workspace_id: project.workspace_id,
      }
      setInitialProjectInfo(projInfo)
      setEditedProjectInfo({ ...projInfo })

      // Load workspace accounts + workspaces list
      if (project.workspace_id) {
        try {
          const [wsAccounts, wsListRes] = await Promise.all([
            socialAccountsApi.listByWorkspace(project.workspace_id),
            workspacesApi.list(),
          ])
          setWorkspaceAccounts(wsAccounts.data)
          setAllWorkspaces(wsListRes.data)
        } catch {
          // Not critical
        }
      }

      setVariantsCount(variantsRes.data.total)
      setTemplatesCount(templatesRes.data.filter((t) => !t.is_deleted).length)

      const pc = pubConfigRes.data
      const editablePub: EditablePublishing = {
        is_paused: pc.is_paused,
        days: pc.days,
        preferred_times: pc.preferred_times,
        depth_days: pc.depth_days,
      }
      setInitialPublishing(editablePub)
      setEditedPublishing({ ...editablePub })

      // Auto-open relevant step if setup incomplete
      if (variantsRes.data.total === 0) {
        setActiveStep(2)
      } else if (
        (project.social_accounts || []).length === 0 ||
        pc.days.length === 0
      ) {
        setActiveStep(6)
      }
    } catch (err) {
      console.error('Failed to load configure data:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Dirty tracking
  const isDirty = useMemo(() => {
    if (!initialSettings || !editedSettings || !initialPublishing || !editedPublishing)
      return false
    const settingsDirty =
      JSON.stringify(initialSettings) !== JSON.stringify(editedSettings)
    const publishingDirty =
      JSON.stringify(initialPublishing) !== JSON.stringify(editedPublishing)
    const projectDirty = showProjectSettings &&
      initialProjectInfo && editedProjectInfo &&
      JSON.stringify(initialProjectInfo) !== JSON.stringify(editedProjectInfo)
    const timezoneDirty = timezone !== initialTimezone
    return settingsDirty || publishingDirty || !!projectDirty || timezoneDirty
  }, [initialSettings, editedSettings, initialPublishing, editedPublishing, initialProjectInfo, editedProjectInfo, showProjectSettings, timezone, initialTimezone])

  // Save
  const handleSave = async () => {
    if (!editedSettings || !editedPublishing) return

    const promises: Promise<unknown>[] = []

    // Settings dirty?
    if (JSON.stringify(initialSettings) !== JSON.stringify(editedSettings)) {
      promises.push(
        templateApi.updateSettings(projectId, {
          llm_model: editedSettings.llm_model as LLMModel,
          preprocessing_prompt: editedSettings.preprocessing_prompt,
          image_model: editedSettings.image_model as ImageModel,
          image_aspect_ratio: editedSettings.image_aspect_ratio as AspectRatio,
          image_prompt_template: editedSettings.image_prompt_template,
          video_model: editedSettings.video_model as VideoModel,
          video_duration: editedSettings.video_duration,
          variant_generation_prompt: editedSettings.variant_generation_prompt || undefined,
          music_mode: editedSettings.music_mode || undefined,
          music_prompt: editedSettings.music_prompt || undefined,
        })
      )
    }

    // Publishing dirty?
    if (JSON.stringify(initialPublishing) !== JSON.stringify(editedPublishing)) {
      promises.push(
        publishingScheduleApi.updateConfig(projectId, {
          enabled: editedPublishing.days.length > 0,
          is_paused: editedPublishing.is_paused,
          days: editedPublishing.days,
          preferred_times: editedPublishing.preferred_times,
          depth_days: editedPublishing.depth_days,
        })
      )
    }

    // Project info dirty?
    if (
      showProjectSettings &&
      initialProjectInfo && editedProjectInfo &&
      JSON.stringify(initialProjectInfo) !== JSON.stringify(editedProjectInfo)
    ) {
      promises.push(
        projectsApi.update(projectId, {
          name: editedProjectInfo.name,
          description: editedProjectInfo.description || undefined,
          workspace_id: editedProjectInfo.workspace_id,
        })
      )
    }

    // Timezone dirty?
    if (timezone !== initialTimezone) {
      promises.push(
        projectsApi.update(projectId, { timezone })
      )
    }

    await Promise.all(promises)

    // Re-fetch settings to get auto-generated variant_generation_prompt
    try {
      const freshSettings = await templateApi.getSettings(projectId)
      const s = freshSettings.data
      setSettings(s)
      const fresh: EditableSettings = {
        llm_model: s.llm_model,
        preprocessing_prompt: s.preprocessing_prompt,
        image_model: s.image_model,
        image_aspect_ratio: s.image_aspect_ratio,
        image_prompt_template: s.image_prompt_template,
        video_model: s.video_model,
        video_duration: s.video_duration,
        variant_generation_prompt: s.variant_generation_prompt || '',
        music_mode: s.music_mode || 'none',
        music_prompt: s.music_prompt || '',
      }
      setInitialSettings(fresh)
      setEditedSettings({ ...fresh })
    } catch {
      // Fallback: just mark current as initial
      setInitialSettings({ ...editedSettings })
    }

    setInitialPublishing({ ...editedPublishing })
    setInitialTimezone(timezone)
    if (editedProjectInfo) setInitialProjectInfo({ ...editedProjectInfo })
  }

  // Discard
  const handleDiscard = () => {
    if (initialSettings) setEditedSettings({ ...initialSettings })
    if (initialPublishing) setEditedPublishing({ ...initialPublishing })
    if (initialProjectInfo) setEditedProjectInfo({ ...initialProjectInfo })
    setTimezone(initialTimezone)
  }

  // Settings field update
  const updateSetting = <K extends keyof EditableSettings>(
    key: K,
    value: EditableSettings[K]
  ) => {
    setEditedSettings((prev) => {
      if (!prev) return prev
      const next = { ...prev, [key]: value }
      // Auto-adjust duration when video model changes
      if (key === 'video_model') {
        next.video_duration = getDefaultDuration(value)
      }
      return next
    })
  }

  // Publishing update
  const updatePublishing = (updates: Partial<EditablePublishing>) => {
    setEditedPublishing((prev) => (prev ? { ...prev, ...updates } : prev))
  }

  // Social account binding (immediate, not through dirty state)
  const handleBindAccount = async (platform: string, accountId: number | null) => {
    setBindingLoading(platform)
    try {
      const currentBound = boundAccounts.find(
        (acc) => acc.platform === platform && acc.is_active
      )
      if (currentBound) {
        await projectsApi.unbindSocialAccount(projectId, currentBound.id)
      }
      if (accountId) {
        const res = await projectsApi.bindSocialAccount(projectId, accountId)
        setBoundAccounts(res.data.social_accounts || [])
      } else {
        setBoundAccounts((prev) => prev.filter((acc) => acc.platform !== platform))
      }
    } catch {
      // silently fail
    } finally {
      setBindingLoading(null)
    }
  }

  // CSV upload success
  const handleCsvUploadSuccess = () => {
    setVariantsRefresh((prev) => prev + 1)
    // Re-fetch variants count
    templateApi
      .listVariants(projectId, { limit: 1 })
      .then((res) => {
        setVariantsCount(res.data.total)
        // Update csv_columns from settings
        templateApi.getSettings(projectId).then((settingsRes) => {
          setSettings(settingsRes.data)
        })
      })
  }

  // Templates count update (called from VideoStep child)
  const handleTemplatesCountChange = (count: number) => {
    setTemplatesCount(count)
  }

  // Step statuses for summary line
  const stepStatuses = useMemo(() => {
    const getModelLabel = (model: string) => {
      const parts = model.split('/')
      return parts[parts.length - 1] || model
    }

    return {
      variants: {
        status: (variantsCount > 0 ? 'complete' : 'empty') as StepStatus,
        summary: variantsCount > 0 ? `${variantsCount} vars` : 'no data',
      },
      preprocessing: {
        status: (editedSettings?.llm_model && editedSettings?.preprocessing_prompt
          ? 'complete'
          : 'incomplete') as StepStatus,
        summary: editedSettings?.llm_model
          ? getModelLabel(editedSettings.llm_model)
          : 'not set',
      },
      image: {
        status: (editedSettings?.image_model && editedSettings?.image_prompt_template
          ? 'complete'
          : 'incomplete') as StepStatus,
        summary: editedSettings?.image_model
          ? `${getModelLabel(editedSettings.image_model)} · ${editedSettings.image_aspect_ratio}`
          : 'not set',
      },
      video: {
        status: (editedSettings?.video_model && templatesCount > 0
          ? 'complete'
          : 'incomplete') as StepStatus,
        summary: editedSettings?.video_model
          ? `${getModelLabel(editedSettings.video_model)} · ${editedSettings.video_duration}s · ${templatesCount} tmpl`
          : 'not set',
      },
      music: {
        status: (editedSettings?.music_mode && editedSettings.music_mode !== 'none' ? 'complete' : 'empty') as StepStatus,
        summary: editedSettings?.music_mode === 'library'
          ? (settings?.audio_hook_retrim
            ? `Hook ${((settings?.audio_hook_duration_ms || 0) / 1000).toFixed(0)}s → ${editedSettings.video_duration}s`
            : `Hook ${((settings?.audio_hook_duration_ms || 0) / 1000).toFixed(0)}s`)
          : editedSettings?.music_mode === 'generate'
          ? (editedSettings.music_prompt?.slice(0, 30) + (editedSettings.music_prompt && editedSettings.music_prompt.length > 30 ? '...' : '') || 'No prompt')
          : 'Disabled',
      },
      distribution: {
        status: (boundAccounts.length > 0 &&
        editedPublishing &&
        editedPublishing.days.length > 0
          ? 'complete'
          : 'empty') as StepStatus,
        summary:
          boundAccounts.length > 0
            ? `${[...new Set(boundAccounts.map((a) => a.platform))].map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(' + ')}`
            : 'no accounts',
      },
    }
  }, [variantsCount, editedSettings, templatesCount, boundAccounts, editedPublishing])

  // Toggle step
  const handleStepToggle = (step: StepNumber) => {
    setActiveStep((prev) => (prev === step ? null : step))
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          <span className="text-sm text-gray-500">Loading pipeline configuration...</span>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Project Settings (Details tab only) */}
      {showProjectSettings && editedProjectInfo && (
        <div className="bg-white rounded-lg border p-6 mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Project</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={editedProjectInfo.name}
                onChange={(e) => setEditedProjectInfo({ ...editedProjectInfo, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={editedProjectInfo.description}
                onChange={(e) => setEditedProjectInfo({ ...editedProjectInfo, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                placeholder="Optional description"
              />
            </div>
            {allWorkspaces.length > 1 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Workspace</label>
                <select
                  value={editedProjectInfo.workspace_id || ''}
                  onChange={(e) => setEditedProjectInfo({ ...editedProjectInfo, workspace_id: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                >
                  {allWorkspaces.map((ws) => (
                    <option key={ws.id} value={ws.id}>{ws.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reference video from Discover */}
      {settings?.reference_video_url && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 flex gap-4 items-start">
          <div className="flex-shrink-0 w-24">
            <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
              <video
                src={settings.reference_video_url}
                controls
                playsInline
                preload="metadata"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-purple-800">Reference Video</p>
            <p className="text-xs text-purple-600 mt-1">Created from Discover — video with selected audio merged</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border">
        {/* Steps accordion — always visible */}
        {editedSettings && editedPublishing && (
          <div>
            {/* Step 1: Preprocessing */}
            <AccordionStep
              step={1}
              title="Preprocessing"
              status={stepStatuses.preprocessing}
              isActive={activeStep === 1}
              onToggle={() => handleStepToggle(1)}
            >
              <PreprocessingStep
                llmModel={editedSettings.llm_model}
                preprocessingPrompt={editedSettings.preprocessing_prompt}
                csvColumns={settings?.csv_columns || null}
                onModelChange={(v) => updateSetting('llm_model', v)}
                onPromptChange={(v) => updateSetting('preprocessing_prompt', v)}
              />
            </AccordionStep>

            {/* Step 2: Variants */}
            <AccordionStep
              step={2}
              title="Variants"
              status={stepStatuses.variants}
              isActive={activeStep === 2}
              onToggle={() => handleStepToggle(2)}
            >
              <InputStep
                projectId={projectId}
                refreshTrigger={variantsRefresh}
                variantGenerationPrompt={editedSettings.variant_generation_prompt}
                onPromptChange={(v) => updateSetting('variant_generation_prompt', v)}
                onCsvUploadSuccess={handleCsvUploadSuccess}
                onVariantsGenerated={handleCsvUploadSuccess}
              />
            </AccordionStep>

            {/* Step 3: Image */}
            <AccordionStep
              step={3}
              title="Image"
              status={stepStatuses.image}
              isActive={activeStep === 3}
              onToggle={() => handleStepToggle(3)}
            >
              <ImageStep
                imageModel={editedSettings.image_model}
                aspectRatio={editedSettings.image_aspect_ratio}
                imagePromptTemplate={editedSettings.image_prompt_template}
                csvColumns={settings?.csv_columns || null}
                onModelChange={(v) => updateSetting('image_model', v)}
                onAspectRatioChange={(v) => updateSetting('image_aspect_ratio', v)}
                onPromptChange={(v) => updateSetting('image_prompt_template', v)}
              />
            </AccordionStep>

            {/* Step 4: Video */}
            <AccordionStep
              step={4}
              title="Video"
              status={stepStatuses.video}
              isActive={activeStep === 4}
              onToggle={() => handleStepToggle(4)}
            >
              <VideoStep
                projectId={projectId}
                videoModel={editedSettings.video_model}
                videoDuration={editedSettings.video_duration}
                onModelChange={(v) => updateSetting('video_model', v)}
                onDurationChange={(v) => updateSetting('video_duration', v)}
                onTemplatesCountChange={handleTemplatesCountChange}
              />
            </AccordionStep>

            {/* Step 5: Music */}
            <AccordionStep
              step={5}
              title="Music"
              status={stepStatuses.music}
              isActive={activeStep === 5}
              onToggle={() => handleStepToggle(5)}
            >
              <div className="space-y-4">
                {/* Mode selector */}
                <div className="flex gap-2">
                  {([
                    { value: 'none', label: 'No Music' },
                    { value: 'library', label: 'Saved Hook' },
                    { value: 'generate', label: 'Generate from Prompt' },
                  ] as const).map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => updateSetting('music_mode', opt.value)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition ${
                        editedSettings.music_mode === opt.value
                          ? 'bg-purple-50 border-purple-300 text-purple-700'
                          : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>

                {/* Library mode — player + info */}
                {editedSettings.music_mode === 'library' && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3 space-y-2">
                    <p className="text-sm text-green-800">
                      {hookPreviewUrl
                        ? `Hook ${((settings?.audio_hook_duration_ms || 0) / 1000).toFixed(0)}s → ${editedSettings.video_duration}s`
                        : 'Using saved audio hook from library'
                      }
                    </p>
                    <audio
                      src={hookPreviewUrl || settings?.audio_hook_url || ''}
                      controls
                      preload="metadata"
                      className="w-full h-8"
                    />
                  </div>
                )}

                {/* Generate mode — prompt */}
                {editedSettings.music_mode === 'generate' && (
                  <div className="space-y-2">
                    <textarea
                      value={editedSettings.music_prompt}
                      onChange={(e) => updateSetting('music_prompt', e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
                      placeholder="e.g. Upbeat electronic lo-fi beat with soft synth pads and a catchy melody"
                    />
                    <p className="text-xs text-gray-400">
                      A new track is generated per batch — best hook is auto-selected and merged with all videos.
                    </p>
                  </div>
                )}

                {/* None mode */}
                {editedSettings.music_mode === 'none' && (
                  <p className="text-sm text-gray-500">
                    Videos will be generated without music.
                  </p>
                )}
              </div>
            </AccordionStep>

            {/* Step 6: Distribution */}
            <AccordionStep
              step={6}
              title="Distribution"
              status={stepStatuses.distribution}
              isActive={activeStep === 6}
              onToggle={() => handleStepToggle(6)}
            >
              <DistributionStep
                projectId={projectId}
                workspaceId={workspaceId}
                boundAccounts={boundAccounts}
                workspaceAccounts={workspaceAccounts}
                bindingLoading={bindingLoading}
                onBindAccount={handleBindAccount}
                publishingConfig={editedPublishing}
                onPublishingChange={updatePublishing}
                timezone={timezone}
                onTimezoneChange={setTimezone}
              />
            </AccordionStep>
          </div>
        )}
      </div>

      <StickySaveBar isDirty={isDirty} onSave={handleSave} onDiscard={handleDiscard} />
    </>
  )
}

// --- Accordion Step ---

function AccordionStep({
  step,
  title,
  status,
  isActive,
  onToggle,
  children,
}: {
  step: number
  title: string
  status: { status: StepStatus; summary: string }
  isActive: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-gray-50 transition"
      >
        <div className="flex items-center gap-3">
          {isActive ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
          <span className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400 bg-gray-100 rounded-full w-5 h-5 flex items-center justify-center">
              {step}
            </span>
            <span className="text-sm font-medium text-gray-900">{title}</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          {status.status === 'complete' ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
          <span className="text-sm text-gray-500">{status.summary}</span>
        </div>
      </button>
      {isActive && <div className="px-6 pb-6">{children}</div>}
    </div>
  )
}
