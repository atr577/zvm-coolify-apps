import { useState, useEffect, useCallback, useMemo } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import {
  templateApi,
  projectsApi,
  socialAccountsApi,
  publishingScheduleApi,
} from '@/services/api'
import type {
  SocialAccount,
  TemplateSettings,
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
}

// Settings that can be edited (preprocessing, image, video fields)
interface EditableSettings {
  llm_model: string
  preprocessing_prompt: string
  image_model: string
  image_aspect_ratio: string
  image_prompt_template: string
  video_model: string
  video_duration: string
}

// Publishing config editable fields
interface EditablePublishing {
  is_paused: boolean
  days: string[]
  preferred_times: string[]
  depth_days: number
}

type StepNumber = 1 | 2 | 3 | 4 | 5

type StepStatus = 'complete' | 'incomplete' | 'empty'

export function ConfigureSection({ projectId }: ConfigureSectionProps) {
  // Expand/collapse
  const [expanded, setExpanded] = useState(false)
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
  const [bindingLoading, setBindingLoading] = useState<string | null>(null)

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
      }
      setInitialSettings(editable)
      setEditedSettings({ ...editable })

      const project = projectRes.data
      setBoundAccounts(project.social_accounts || [])
      setWorkspaceId(project.workspace_id)
      setTimezone(project.timezone || 'UTC')

      // Load workspace accounts
      if (project.workspace_id) {
        try {
          const wsAccounts = await socialAccountsApi.listByWorkspace(project.workspace_id)
          setWorkspaceAccounts(wsAccounts.data)
        } catch {
          // Workspace accounts may fail — not critical
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

      // Auto-expand logic
      if (variantsRes.data.total === 0) {
        setExpanded(true)
        setActiveStep(1)
      } else if (
        (project.social_accounts || []).length === 0 ||
        pc.days.length === 0
      ) {
        setExpanded(true)
        setActiveStep(5)
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
    return settingsDirty || publishingDirty
  }, [initialSettings, editedSettings, initialPublishing, editedPublishing])

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

    await Promise.all(promises)

    // Update initial to match current (no longer dirty)
    setInitialSettings({ ...editedSettings })
    setInitialPublishing({ ...editedPublishing })
  }

  // Discard
  const handleDiscard = () => {
    if (initialSettings) setEditedSettings({ ...initialSettings })
    if (initialPublishing) setEditedPublishing({ ...initialPublishing })
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
      input: {
        status: (variantsCount > 0 ? 'complete' : 'empty') as StepStatus,
        summary: variantsCount > 0 ? `${variantsCount} vars` : 'no CSV',
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
          ? `${getModelLabel(editedSettings.video_model)} · ${templatesCount} tmpl`
          : 'not set',
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
      <div className="bg-white rounded-lg border">
        {/* Header */}
        <button
          onClick={() => {
            setExpanded(!expanded)
            if (!expanded && activeStep === null) setActiveStep(1)
          }}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition"
        >
          <div className="flex items-center gap-3">
            {expanded ? (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-gray-400" />
            )}
            <h2 className="text-lg font-medium text-gray-900">Configure</h2>
          </div>
          {!expanded && (
            <span className="text-sm text-gray-500">Expand</span>
          )}
        </button>

        {/* Summary line (when collapsed) */}
        {!expanded && (
          <div className="px-6 pb-4 -mt-2">
            <SummaryLine statuses={stepStatuses} />
          </div>
        )}

        {/* Accordion (when expanded) */}
        {expanded && editedSettings && editedPublishing && (
          <div className="border-t">
            {/* Step 1: Input */}
            <AccordionStep
              step={1}
              title="Input"
              status={stepStatuses.input}
              isActive={activeStep === 1}
              onToggle={() => handleStepToggle(1)}
            >
              <InputStep
                projectId={projectId}
                refreshTrigger={variantsRefresh}
                onCsvUploadSuccess={handleCsvUploadSuccess}
              />
            </AccordionStep>

            {/* Step 2: Preprocessing */}
            <AccordionStep
              step={2}
              title="Preprocessing"
              status={stepStatuses.preprocessing}
              isActive={activeStep === 2}
              onToggle={() => handleStepToggle(2)}
            >
              <PreprocessingStep
                llmModel={editedSettings.llm_model}
                preprocessingPrompt={editedSettings.preprocessing_prompt}
                csvColumns={settings?.csv_columns || null}
                onModelChange={(v) => updateSetting('llm_model', v)}
                onPromptChange={(v) => updateSetting('preprocessing_prompt', v)}
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

            {/* Step 5: Distribution */}
            <AccordionStep
              step={5}
              title="Distribution"
              status={stepStatuses.distribution}
              isActive={activeStep === 5}
              onToggle={() => handleStepToggle(5)}
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
              />
            </AccordionStep>
          </div>
        )}
      </div>

      <StickySaveBar isDirty={isDirty} onSave={handleSave} onDiscard={handleDiscard} />
    </>
  )
}

// --- Summary Line ---

function SummaryLine({
  statuses,
}: {
  statuses: Record<string, { status: StepStatus; summary: string }>
}) {
  const entries = [
    { key: 'input', label: 'Input' },
    { key: 'preprocessing', label: 'Preproc' },
    { key: 'image', label: 'Image' },
    { key: 'video', label: 'Video' },
    { key: 'distribution', label: 'Distribution' },
  ]

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      {entries.map((entry, idx) => {
        const s = statuses[entry.key]
        return (
          <span key={entry.key} className="flex items-center gap-1">
            {s.status === 'complete' ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-red-400" />
            )}
            <span className="text-gray-500">{entry.label}:</span>
            <span className="text-gray-700">{s.summary}</span>
            {idx < entries.length - 1 && (
              <span className="text-gray-300 ml-1">·</span>
            )}
          </span>
        )
      })}
    </div>
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
