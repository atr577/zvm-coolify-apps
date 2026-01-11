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
  Play,
  Image as ImageIcon,
  Video,
  Volume2,
  FileText,
} from 'lucide-react'
import { useWorkflowV3 } from '@/hooks/useWorkflowV3'
import type { Video as VideoType } from '@/types'

interface StepReviewProps {
  video: VideoType
  videoId: number
  currentStep: string
  steps: string[]
  completedSteps: string[]
  onGenerate: () => void
  onRegenerate: () => void
  isGenerating: boolean
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
  onGenerate,
  onRegenerate,
  isGenerating,
}: StepReviewProps) {
  const [showHistory, setShowHistory] = useState(false)
  const isRemix = video.project?.project_type === 'remix'
  const workflow = useWorkflowV3(videoId, isRemix)

  // Get variants for current step
  const { data: variantsData } = workflow.useVariants(currentStep)
  const variants = variantsData?.variants || []

  // Check if current step is completed (has data)
  const isStepCompleted = completedSteps.includes(currentStep)
  const stepContent = getStepContent(video, currentStep)
  const stepIndex = steps.indexOf(currentStep)
  const isLastStep = stepIndex === steps.length - 1

  // If step has no content yet, show generate button
  if (!isStepCompleted && !isGenerating) {
    return (
      <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
          <div className="flex items-center space-x-3">
            {getStepIcon(currentStep)}
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Step {stepIndex + 1}: {STEP_LABELS[currentStep]}
              </h2>
              <p className="text-sm text-gray-600">Ready to generate</p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="w-full flex items-center justify-center px-6 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
          >
            {isGenerating ? (
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
            ) : (
              <Play className="h-5 w-5 mr-2" />
            )}
            {isGenerating ? 'Generating...' : `Generate ${STEP_LABELS[currentStep]}`}
          </button>
        </div>
      </div>
    )
  }

  // Show content with approve/regenerate
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
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
            {/* Step content */}
            <div className="mb-6">
              <StepContentDisplay step={currentStep} content={stepContent} />
            </div>

            {/* History panel */}
            {showHistory && variants.length > 0 && (
              <div className="mb-6 border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <span className="text-sm font-medium text-gray-700">Variant History</span>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {variants.map((variant: { id: number; is_selected: boolean; created_at: string }, i: number) => (
                    <button
                      key={variant.id}
                      onClick={() => workflow.selectVariant(variant.id)}
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
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex space-x-3">
              <button
                onClick={() => workflow.generateStep(steps[stepIndex + 1] || currentStep)}
                disabled={isLastStep}
                className="flex-1 flex items-center justify-center px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition disabled:opacity-50"
              >
                <CheckCircle className="h-5 w-5 mr-2" />
                {isLastStep ? 'Complete' : 'Approve & Continue'}
                {!isLastStep && <ChevronRight className="h-4 w-4 ml-1" />}
              </button>
              <button
                onClick={onRegenerate}
                disabled={isGenerating}
                className="flex items-center justify-center px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
              >
                <RefreshCw className="h-5 w-5 mr-2" />
                Regenerate
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
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
