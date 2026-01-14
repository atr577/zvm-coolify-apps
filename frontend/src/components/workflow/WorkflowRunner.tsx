/**
 * WorkflowRunner - Main workflow component for V3
 *
 * Handles both AUTO and MANUAL modes:
 * - AUTO: Shows progress, runs all steps
 * - MANUAL: Shows step-by-step with approval
 */
import { useEffect, useRef } from 'react'
import { CheckCircle, Circle, Loader2, Play, AlertCircle, RefreshCw } from 'lucide-react'
import { useWorkflowV3 } from '@/hooks/useWorkflowV3'
import StepReview from './StepReview'
import type { Video } from '@/types'

interface WorkflowRunnerProps {
  video: Video
  videoId: number
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

export default function WorkflowRunner({ video, videoId }: WorkflowRunnerProps) {
  const isRemix = video.project?.project_type === 'remix'
  const isManual = video.workflow_mode === 'MANUAL'
  const includeAudio = video.project?.audio_mode !== 'none'

  const workflow = useWorkflowV3(videoId, isRemix, includeAudio)
  const steps = workflow.steps  // Use steps from hook (respects includeAudio)

  // Ref to prevent double auto-start (React StrictMode protection)
  const autoStartedRef = useRef(false)

  // Use video.current_step from backend to determine state
  const currentStep = video.current_step as string | null

  // Completed steps: all steps that have data (for navigation)
  const completedSteps = getCompletedSteps(video, steps)
  const isCompleted = video.status === 'completed'

  // Check if current step has data (awaiting approval)
  const currentStepHasData = currentStep ? hasStepData(video, currentStep) : false

  // AUTO mode: auto-start when pending or in_progress (resume after refresh)
  useEffect(() => {
    const status = video.status?.toLowerCase()
    const shouldAutoStart = !isManual &&
      (status === 'pending' || (status === 'in_progress' && !isCompleted)) &&
      !workflow.isRunningAuto &&
      !autoStartedRef.current

    if (shouldAutoStart) {
      autoStartedRef.current = true
      workflow.runAuto()
    }
  }, [isManual, video.status, isCompleted, workflow.isRunningAuto])

  // MANUAL mode: auto-start current step if it has no data
  // Skip if video is already IN_PROGRESS (backend is generating)
  const isBackendGenerating = video.status?.toLowerCase() === 'in_progress'

  useEffect(() => {
    if (
      isManual &&
      !isCompleted &&
      currentStep &&
      !currentStepHasData &&
      !workflow.isGenerating &&
      !workflow.error &&
      !isBackendGenerating  // Don't start if backend already generating
    ) {
      workflow.generateStep(currentStep as typeof steps[number])
    }
  }, [isManual, isCompleted, currentStep, currentStepHasData, workflow.isGenerating, workflow.error, isBackendGenerating])

  // Error display
  if (workflow.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <div className="flex items-center space-x-3 mb-4">
          <AlertCircle className="h-6 w-6 text-red-500" />
          <h3 className="text-lg font-semibold text-red-700">Generation Failed</h3>
        </div>
        <p className="text-red-600 mb-4">{workflow.error}</p>
        <button
          onClick={() => {
            workflow.clearError()
            if (currentStep) {
              workflow.generateStep(currentStep as typeof steps[number])
            }
          }}
          className="flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </button>
      </div>
    )
  }

  // MANUAL mode: show approval UI when current step has data
  if (isManual && currentStep && currentStepHasData && !workflow.isGenerating) {
    const stepAsType = currentStep as typeof steps[number]
    return (
      <StepReview
        video={video}
        videoId={videoId}
        currentStep={stepAsType}
        steps={[...steps]}
        completedSteps={completedSteps}
      />
    )
  }

  // Combined generating state (frontend request OR backend still processing)
  const isAnyGenerating = workflow.isGenerating || isBackendGenerating

  // Progress view (AUTO mode or MANUAL generating)
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
        <div className="flex items-center space-x-3">
          {isAnyGenerating ? (
            <Loader2 className="h-6 w-6 text-purple-600 animate-spin" />
          ) : isCompleted ? (
            <CheckCircle className="h-6 w-6 text-green-500" />
          ) : (
            <Play className="h-6 w-6 text-purple-600" />
          )}
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              {isCompleted
                ? 'Generation Complete'
                : isAnyGenerating
                ? `Generating ${STEP_LABELS[workflow.generatingStep || currentStep || ''] || '...'}`
                : 'Ready to Generate'}
            </h2>
            <p className="text-sm text-gray-600">
              {completedSteps.length} of {steps.length} steps completed
            </p>
          </div>
        </div>
      </div>

      {/* Steps list */}
      <div className="p-6">
        <div className="space-y-3">
          {steps.map((step, index) => {
            const isStepCompleted = completedSteps.includes(step)
            const isCurrent = step === (workflow.generatingStep || currentStep)
            // Show spinner if frontend generating OR backend still processing this step
            const isGeneratingThis = workflow.generatingStep === step ||
              (isBackendGenerating && step === currentStep && !isStepCompleted) ||
              (!isManual && workflow.isRunningAuto && step === currentStep && !isStepCompleted)

            return (
              <div
                key={step}
                className={`flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  isGeneratingThis
                    ? 'bg-purple-50 border border-purple-200'
                    : isStepCompleted
                    ? 'bg-green-50'
                    : isCurrent && !isManual
                    ? 'bg-blue-50'
                    : 'bg-gray-50'
                }`}
              >
                <div className="flex-shrink-0">
                  {isStepCompleted ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : isGeneratingThis ? (
                    <Loader2 className="h-5 w-5 text-purple-600 animate-spin" />
                  ) : (
                    <Circle className="h-5 w-5 text-gray-300" />
                  )}
                </div>
                <span className="text-sm text-gray-500 w-8">#{index + 1}</span>
                <span
                  className={`flex-1 font-medium ${
                    isGeneratingThis
                      ? 'text-purple-700'
                      : isStepCompleted
                      ? 'text-green-700'
                      : 'text-gray-400'
                  }`}
                >
                  {STEP_LABELS[step] || step}
                </span>
                {isGeneratingThis && (
                  <span className="text-xs text-purple-600 animate-pulse">Processing...</span>
                )}
              </div>
            )
          })}
        </div>

      </div>
    </div>
  )
}

// Helper: Get completed steps (all steps that have data, regardless of current position)
function getCompletedSteps(video: Video, steps: readonly string[]): string[] {
  const completed: string[] = []

  for (const step of steps) {
    if (hasStepData(video, step)) {
      completed.push(step)
    }
  }

  return completed
}

// Helper: Check if step has data in video
function hasStepData(video: Video, step: string): boolean {
  switch (step) {
    case 'story':
      return !!video.story_data
    case 'description':
      return !!video.description_data
    case 'prompt':
      return !!video.prompt_data
    case 'image':
      return !!video.image_url
    case 'scenario':
      return !!video.scenario_data
    case 'video':
      return !!video.video_url
    case 'audio':
      return !!video.audio_data || !!video.video_with_audio_url
    default:
      return false
  }
}
