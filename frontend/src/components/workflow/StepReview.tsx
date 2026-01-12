/**
 * StepReview - Review step content in MANUAL mode
 *
 * Shows:
 * - Current step content (text, image, video, audio)
 * - Approve / Regenerate buttons
 * - History of variants
 */
import { useState } from 'react'
import {
  CheckCircle,
  RefreshCw,
  History,
  ChevronRight,
  Loader2,
  Image as ImageIcon,
  Video,
  Volume2,
  FileText,
  Edit2,
  Save,
  X,
} from 'lucide-react'
import { useWorkflowV3, StepType } from '@/hooks/useWorkflowV3'
import HookSelector, { AiMusicVariant } from '@/components/video/HookSelector'
import type { Video as VideoType } from '@/types'

interface StepReviewProps {
  video: VideoType
  videoId: number
  currentStep: StepType
  steps: StepType[]
  completedSteps: string[]
}

// Step labels
const STEP_LABELS: Record<string, string> = {
  story: 'Story',
  description: 'Description',
  prompt: 'Image Prompt',
  image: 'Image',
  scenario: 'Scenario',
  video: 'Video',
  audio: 'Audio',
}

export default function StepReview({
  video,
  videoId,
  currentStep,
  steps,
  completedSteps,
}: StepReviewProps) {
  // completedSteps is available for future use (e.g., showing progress)
  void completedSteps

  const [showHistory, setShowHistory] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editedContent, setEditedContent] = useState<string>('')
  const [feedback, setFeedback] = useState('')
  const isRemix = video.project?.project_type === 'remix'
  const includeAudio = video.project?.audio_mode !== 'none'
  const workflow = useWorkflowV3(videoId, isRemix, includeAudio)

  // Use workflow's isGenerating state (not from props)
  const isGenerating = workflow.generatingStep === currentStep

  // Get variants for current step
  const { data: variantsData } = workflow.useVariants(currentStep)
  const variants = variantsData?.variants || []
  const currentVariant = variants.find(v => v.is_selected) || variants[0]

  // Use content from selected variant, fallback to video data
  const stepContent = currentVariant?.content
    ? getContentForDisplay(currentStep, currentVariant.content)
    : getStepContent(video, currentStep)
  const stepIndex = steps.indexOf(currentStep)
  const isLastStep = stepIndex === steps.length - 1

  // Check if step content is editable (text-based steps)
  const isEditableStep = ['scenario'].includes(currentStep)

  // Check if this is ai_music audio step
  const isAiMusicAudio = currentStep === 'audio' &&
    currentVariant?.content?.provider === 'ai_music'

  // Selected hook index for ai_music (find selected variant index)
  const [selectedHookIndex, setSelectedHookIndex] = useState(0)

  // Convert variants to AiMusicVariant format for HookSelector
  const aiMusicVariants: AiMusicVariant[] = isAiMusicAudio
    ? variants
        .filter(v => v.content?.hook)
        .map((v, idx) => {
          const content = v.content as Record<string, any>
          return {
            hook: content.hook,
            preview_url: (content.preview_url || content.local_path || '') as string,
            video_id: (content.video_id || video.id) as number,
            index: idx,
          }
        })
    : []

  // Handle approve (move to next step)
  const handleApprove = async () => {
    if (!currentVariant) return
    setIsApproving(true)
    try {
      workflow.approveVariant(currentVariant.id)
    } finally {
      setIsApproving(false)
    }
  }

  // Handle edit mode
  const handleStartEdit = () => {
    setEditedContent(JSON.stringify(stepContent, null, 2))
    setIsEditing(true)
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
    setEditedContent('')
  }

  const handleSaveEdit = async () => {
    try {
      const parsed = JSON.parse(editedContent)
      workflow.updateContent(currentStep, parsed)
      setIsEditing(false)
    } catch (e) {
      alert('Invalid JSON format')
    }
  }

  // Handle regenerate with feedback
  const handleRegenerate = () => {
    workflow.generateStep(currentStep, feedback || undefined)
    setFeedback('')
  }

  // Check if a step has data (is completed)
  const hasStepData = (step: string) => completedSteps.includes(step) || step === currentStep

  // Handle step click (navigate back)
  const handleStepClick = (step: string) => {
    if (step !== currentStep && hasStepData(step)) {
      workflow.gotoStep(step as typeof steps[number])
    }
  }

  // Show content with approve/regenerate
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
      {/* Step Navigation */}
      <div className="flex items-center justify-center py-3 px-4 bg-gray-50 border-b">
        {steps.map((step, idx) => {
          const isCompleted = completedSteps.includes(step)
          const isCurrent = step === currentStep
          const isClickable = isCompleted && !isCurrent

          return (
            <div key={step} className="flex items-center">
              <button
                onClick={() => handleStepClick(step)}
                disabled={!isClickable}
                className={`flex items-center px-3 py-1 rounded-full text-sm font-medium transition ${
                  isCurrent
                    ? 'bg-purple-600 text-white'
                    : isCompleted
                    ? 'bg-green-100 text-green-700 hover:bg-green-200 cursor-pointer'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                <span className="mr-1">{idx + 1}</span>
                {STEP_LABELS[step]}
              </button>
              {idx < steps.length - 1 && (
                <ChevronRight className="h-4 w-4 text-gray-300 mx-1" />
              )}
            </div>
          )
        })}
      </div>

      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getStepIcon(currentStep)}
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Step {stepIndex + 1}: {STEP_LABELS[currentStep]}
              </h2>
              <p className="text-sm text-gray-600">
                {isGenerating ? 'Generating...' : 'Review and approve'}
              </p>
            </div>
          </div>
          {variants.length > 1 && (
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center px-3 py-1 text-sm text-purple-600 hover:bg-purple-50 rounded-lg"
            >
              <History className="h-4 w-4 mr-1" />
              {variants.length} variants
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {isGenerating ? (
          <div className="flex flex-col items-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-purple-600 mb-4" />
            <p className="text-gray-600">Generating {STEP_LABELS[currentStep]}...</p>
          </div>
        ) : (
          <>
            {/* Step content with edit option */}
            <div className="mb-6">
              {isEditing ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Edit Content</span>
                    <div className="flex space-x-2">
                      <button
                        onClick={handleSaveEdit}
                        className="flex items-center px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                      >
                        <Save className="h-4 w-4 mr-1" />
                        Save
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="flex items-center px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                      >
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                      </button>
                    </div>
                  </div>
                  <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full h-64 px-3 py-2 font-mono text-sm border rounded-lg focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              ) : isAiMusicAudio && aiMusicVariants.length > 0 ? (
                /* AI Music Hook Selector */
                <HookSelector
                  videoUrl={video.video_url || ''}
                  variants={aiMusicVariants}
                  selectedIndex={selectedHookIndex}
                  onSelect={(idx) => {
                    setSelectedHookIndex(idx)
                    // Switch to corresponding variant
                    const variant = variants.find(v => v.content?.index === idx)
                    if (variant) {
                      workflow.switchVariant(variant.id)
                    }
                  }}
                  onConfirm={handleApprove}
                  isLoading={isApproving}
                  musicPrompt={(currentVariant?.content as Record<string, any>)?.music_prompt as string | undefined}
                />
              ) : (
                <div className="relative">
                  {isEditableStep && (
                    <button
                      onClick={handleStartEdit}
                      className="absolute top-2 right-2 flex items-center px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 z-10"
                    >
                      <Edit2 className="h-3 w-3 mr-1" />
                      Edit
                    </button>
                  )}
                  <StepContentDisplay step={currentStep} content={stepContent} />
                </div>
              )}
            </div>

            {/* History panel */}
            {showHistory && variants.length > 0 && (
              <div className="mb-6 border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <span className="text-sm font-medium text-gray-700">Variant History</span>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {variants.map((variant: { id: number; is_selected: boolean; created_at: string; feedback?: string }, i: number) => (
                    <button
                      key={variant.id}
                      onClick={() => workflow.switchVariant(variant.id)}
                      className={`w-full text-left px-4 py-2 border-b last:border-0 hover:bg-gray-50 ${
                        variant.is_selected ? 'bg-purple-50' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm">
                          Variant {variants.length - i}
                          {variant.is_selected && (
                            <span className="ml-2 text-xs text-purple-600">(selected)</span>
                          )}
                        </span>
                        <span className="text-xs text-gray-400">
                          {new Date(variant.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      {variant.feedback && (
                        <p className="text-xs text-gray-500 mt-1 truncate">
                          💬 {variant.feedback}
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Feedback input and Actions - hide for ai_music (HookSelector has its own) */}
            {!isAiMusicAudio && (
              <>
                {/* Feedback input for regeneration */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Feedback (optional)
                  </label>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Describe what to change..."
                    className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 resize-none"
                    rows={2}
                  />
                </div>

                {/* Actions */}
                <div className="flex space-x-3">
                  <button
                    onClick={handleApprove}
                    disabled={isApproving || !currentVariant || isEditing}
                    className="flex-1 flex items-center justify-center px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                  >
                    {isApproving ? (
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle className="h-5 w-5 mr-2" />
                    )}
                    {isLastStep ? 'Complete' : 'Approve & Continue'}
                    {!isLastStep && !isApproving && <ChevronRight className="h-4 w-4 ml-1" />}
                  </button>
                  <button
                    onClick={handleRegenerate}
                    disabled={isGenerating || isApproving || isEditing}
                    className="flex items-center justify-center px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
                  >
                    <RefreshCw className="h-5 w-5 mr-2" />
                    Regenerate
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// Helper: Extract display content from variant content
function getContentForDisplay(step: string, content: Record<string, unknown>): unknown {
  switch (step) {
    case 'image':
      return content.image_url
    case 'video':
      return content.video_url
    case 'audio':
      return content.audio_url || content.video_with_audio_url
    case 'scenario':
      return content  // Return full scenario object
    default:
      return content
  }
}

// Helper: Get step content from video
function getStepContent(video: VideoType, step: string): unknown {
  switch (step) {
    case 'story':
      return video.story_data
    case 'description':
      return video.description_data
    case 'prompt':
      return video.prompt_data
    case 'image':
      return video.image_url
    case 'scenario':
      return video.scenario_data
    case 'video':
      return video.video_url
    case 'audio':
      return video.video_with_audio_url
    default:
      return null
  }
}

// Helper: Get step icon
function getStepIcon(step: string) {
  const className = 'h-6 w-6 text-purple-600'
  switch (step) {
    case 'image':
      return <ImageIcon className={className} />
    case 'video':
      return <Video className={className} />
    case 'audio':
      return <Volume2 className={className} />
    default:
      return <FileText className={className} />
  }
}

// Step content display
function StepContentDisplay({
  step,
  content,
}: {
  step: string
  content: unknown
}) {
  if (!content) {
    return <p className="text-gray-400 italic">No content yet</p>
  }

  switch (step) {
    case 'image':
      return (
        <div className="flex justify-center">
          <img
            src={content as string}
            alt="Generated"
            className="max-h-96 rounded-lg shadow-lg"
          />
        </div>
      )

    case 'video':
      return (
        <div className="flex justify-center">
          <video
            src={content as string}
            controls
            className="max-h-96 rounded-lg shadow-lg"
          />
        </div>
      )

    case 'audio':
      return (
        <div className="flex justify-center">
          <video
            src={content as string}
            controls
            className="max-h-96 rounded-lg shadow-lg"
          />
        </div>
      )

    case 'story':
    case 'description':
    case 'prompt':
    case 'scenario':
      return (
        <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
          <JsonDisplay data={content} />
        </div>
      )

    default:
      return <pre className="text-sm">{JSON.stringify(content, null, 2)}</pre>
  }
}

// JSON display helper
function JsonDisplay({ data }: { data: unknown }) {
  if (!data || typeof data !== 'object') {
    return <span>{String(data)}</span>
  }

  return (
    <div className="space-y-2">
      {Object.entries(data as Record<string, unknown>).map(([key, value]) => (
        <div key={key}>
          <span className="text-sm font-medium text-gray-700">{key}: </span>
          <span className="text-sm text-gray-600">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  )
}
