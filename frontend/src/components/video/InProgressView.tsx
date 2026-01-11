import {
  XCircle, Play, Loader2, Volume2, CheckCircle,
  ThumbsUp, RotateCcw, Edit2, Circle
} from 'lucide-react'
import { CustomPrompt } from '@/services/api'
import { getStepLabel } from '@/utils/video'
import PublishingSettings from '@/components/PublishingSettings'
import PromptEditor from '@/components/PromptEditor'
import { StatusIcon, StepsList, StepContentRenderer } from '@/components/video'
import { ImagePromptEditor, VideoPromptEditor } from './PromptEditors'
import type { Video, WorkflowStep } from '@/types'

interface WorkflowState {
  feedback: string
  setFeedback: (v: string) => void
  selectedAudioVariant: number | null
  setSelectedAudioVariant: (v: number | null) => void
  regeneratingStep: string | null
  customPrompts: Record<string, CustomPrompt | null>
  editedImagePrompt: { main_prompt: string; negative_prompt: string; style_suffix: string } | null
  setEditedImagePrompt: (v: any) => void
  editedVideoPrompt: { motion_prompt: string } | null
  setEditedVideoPrompt: (v: any) => void
  handlePromptChange: (stepType: string, prompt: CustomPrompt | null) => void
  handleRegenerateStep: (stepType: string) => void
  approveStepMutation: { mutate: (args: any) => void; isLoading: boolean }
  selectAudioMutation: { mutate: (idx: number) => void; isLoading: boolean }
}

interface InProgressViewProps {
  video: Video
  videoId: number
  steps: WorkflowStep[]
  currentStep: WorkflowStep | undefined
  pendingSteps: WorkflowStep[]
  failedStep: WorkflowStep | undefined
  completedCount: number
  totalSteps: number
  isPublishing: boolean
  workflow: WorkflowState
}

export default function InProgressView({
  video,
  videoId,
  steps,
  currentStep,
  pendingSteps,
  failedStep,
  completedCount,
  totalSteps,
  isPublishing,
  workflow
}: InProgressViewProps) {
  const {
    feedback, setFeedback,
    selectedAudioVariant, setSelectedAudioVariant,
    regeneratingStep,
    customPrompts,
    editedImagePrompt, setEditedImagePrompt,
    editedVideoPrompt, setEditedVideoPrompt,
    handlePromptChange,
    handleRegenerateStep,
    approveStepMutation,
    selectAudioMutation
  } = workflow

  // For AUTO mode in_progress, show AutoProgressView
  const isAutoInProgress = video.workflow_mode !== 'MANUAL' && video.status?.toLowerCase() === 'in_progress'

  return (
    <div className="space-y-6">
      {/* AUTO mode progress display */}
      {isAutoInProgress && (
        <AutoProgressView video={video} steps={steps} />
      )}

      {/* First step - Story for Discover, Image for Remix */}
      {!isAutoInProgress && video.workflow_mode === 'MANUAL' && steps.length === 0 && (
        video.project?.project_type === 'remix' ? (
          <RemixStartCard
            video={video}
            regeneratingStep={regeneratingStep}
            onGenerate={() => handleRegenerateStep('image')}
          />
        ) : (
          <ManualStartCard
            video={video}
            videoId={videoId}
            regeneratingStep={regeneratingStep}
            customPrompts={customPrompts}
            onPromptChange={handlePromptChange}
            onGenerate={() => handleRegenerateStep('story')}
          />
        )
      )}

      {/* Publishing Settings */}
      {isPublishing && video.adaptation_data && (
        <PublishingSettings
          videoId={videoId}
          publishingStepId={steps.find(s => s.step_type === 'publishing')?.id || 0}
          adaptationData={video.adaptation_data}
          platforms={video.project?.platforms || []}
          videoUrl={video.video_with_audio_url || video.video_url || ''}
        />
      )}

      {/* Current Step Card (MANUAL mode only) */}
      {!isAutoInProgress && currentStep && !isPublishing && (
        <CurrentStepCard
          step={currentStep}
          stepIndex={steps.indexOf(currentStep)}
          audioVariants={video.audio_variants || undefined}
          selectedAudioVariant={selectedAudioVariant}
          setSelectedAudioVariant={setSelectedAudioVariant}
          feedback={feedback}
          setFeedback={setFeedback}
          regeneratingStep={regeneratingStep}
          onApprove={(approved, fb) => approveStepMutation.mutate({
            stepId: currentStep.id,
            approved,
            feedback: fb,
            stepType: currentStep.step_type
          })}
          onSelectAudio={(idx) => selectAudioMutation.mutate(idx)}
          isApproving={approveStepMutation.isLoading}
          isSelectingAudio={selectAudioMutation.isLoading}
        />
      )}

      {/* Failed step (MANUAL mode only) */}
      {!isAutoInProgress && failedStep && !currentStep && (
        <FailedStepCard
          step={failedStep}
          stepIndex={steps.indexOf(failedStep)}
          video={video}
          videoId={videoId}
          regeneratingStep={regeneratingStep}
          customPrompts={customPrompts}
          onPromptChange={handlePromptChange}
          onRegenerate={() => handleRegenerateStep(failedStep.step_type)}
        />
      )}

      {/* Pending step (MANUAL mode only) */}
      {!isAutoInProgress && !currentStep && !failedStep && pendingSteps.length > 0 && !isPublishing && (
        <PendingStepCard
          step={pendingSteps[0]}
          video={video}
          videoId={videoId}
          regeneratingStep={regeneratingStep}
          customPrompts={customPrompts}
          editedImagePrompt={editedImagePrompt}
          setEditedImagePrompt={setEditedImagePrompt}
          editedVideoPrompt={editedVideoPrompt}
          setEditedVideoPrompt={setEditedVideoPrompt}
          onPromptChange={handlePromptChange}
          onGenerate={() => handleRegenerateStep(pendingSteps[0].step_type)}
        />
      )}

      {/* Steps Progress (hidden during AUTO in_progress since AutoProgressView shows it) */}
      {!isAutoInProgress && (
        <StepsList
          steps={steps}
          completedCount={completedCount}
          totalSteps={totalSteps}
          currentStepId={currentStep?.id}
          showProgress
        />
      )}
    </div>
  )
}

// Manual Start Card
function ManualStartCard({
  video,
  videoId,
  regeneratingStep,
  customPrompts,
  onPromptChange,
  onGenerate
}: {
  video: Video
  videoId: number
  regeneratingStep: string | null
  customPrompts: Record<string, CustomPrompt | null>
  onPromptChange: (stepType: string, prompt: CustomPrompt | null) => void
  onGenerate: () => void
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
        <div className="flex items-center space-x-3">
          <Play className="h-6 w-6 text-purple-600" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">Step 1: Story</h2>
            <p className="text-sm text-gray-600">Generate the story concept</p>
          </div>
        </div>
      </div>
      <div className="p-6 space-y-4">
        <PromptEditor
          videoId={videoId}
          stepType="story"
          context={{
            theme: video.project?.story_template,
            duration: video.project?.duration,
            platforms: video.project?.platforms
          }}
          onPromptChange={(customPrompt) => onPromptChange('story', customPrompt)}
          disabled={!!regeneratingStep}
        />
        <button
          onClick={onGenerate}
          disabled={!!regeneratingStep}
          className="w-full flex items-center justify-center px-6 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
        >
          {regeneratingStep === 'story' ? (
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          ) : (
            <Play className="h-5 w-5 mr-2" />
          )}
          {regeneratingStep === 'story' ? 'Generating...' : 'Generate Story'}
          {customPrompts['story'] && (
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
              <Edit2 className="h-3 w-3 mr-1" />
              Custom
            </span>
          )}
        </button>
      </div>
    </div>
  )
}

// Remix Start Card (starts at Image, not Story)
function RemixStartCard({
  video,
  regeneratingStep,
  onGenerate
}: {
  video: Video
  regeneratingStep: string | null
  onGenerate: () => void
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
        <div className="flex items-center space-x-3">
          <Play className="h-6 w-6 text-purple-600" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">Step 1: Image</h2>
            <p className="text-sm text-gray-600">Generate image from template</p>
          </div>
        </div>
      </div>
      <div className="p-6 space-y-4">
        {video.image_prompt && (
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Image Prompt:</p>
            <p className="text-sm text-gray-600">{video.image_prompt}</p>
          </div>
        )}
        <button
          onClick={onGenerate}
          disabled={!!regeneratingStep}
          className="w-full flex items-center justify-center px-6 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
        >
          {regeneratingStep === 'image' ? (
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          ) : (
            <Play className="h-5 w-5 mr-2" />
          )}
          {regeneratingStep === 'image' ? 'Generating...' : 'Generate Image'}
        </button>
      </div>
    </div>
  )
}

// Current Step Card
function CurrentStepCard({
  step,
  stepIndex,
  audioVariants,
  selectedAudioVariant,
  setSelectedAudioVariant,
  feedback,
  setFeedback,
  regeneratingStep,
  onApprove,
  onSelectAudio,
  isApproving,
  isSelectingAudio
}: {
  step: WorkflowStep
  stepIndex: number
  audioVariants?: string[]
  selectedAudioVariant: number | null
  setSelectedAudioVariant: (v: number | null) => void
  feedback: string
  setFeedback: (v: string) => void
  regeneratingStep: string | null
  onApprove: (approved: boolean, feedback?: string) => void
  onSelectAudio: (idx: number) => void
  isApproving: boolean
  isSelectingAudio: boolean
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <StatusIcon status={step.status} size={6} />
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Step {stepIndex + 1}: {getStepLabel(step.step_type)}
              </h2>
              <p className="text-sm text-gray-600 capitalize">
                {step.status.replace('_', ' ')}
              </p>
            </div>
          </div>
          {step.generation_time_seconds && (
            <span className="text-sm text-gray-500">
              {step.generation_time_seconds.toFixed(1)}s
            </span>
          )}
        </div>
      </div>

      <div className="p-6">
        {step.step_type === 'image' && step.content?.image_url && (
          <div className="mb-6">
            <img src={step.content.image_url} alt="Preview" className="max-h-96 mx-auto rounded-lg shadow" />
          </div>
        )}
        {step.step_type === 'video' && step.content?.video_url && (
          <div className="mb-6">
            <video src={step.content.video_url} controls className="max-h-96 mx-auto rounded-lg shadow" />
          </div>
        )}

        {step.step_type === 'audio' && audioVariants && audioVariants.length > 0 && (
          <AudioVariantSelection
            audioVariants={audioVariants}
            selectedAudioVariant={selectedAudioVariant}
            setSelectedAudioVariant={setSelectedAudioVariant}
            onSelect={onSelectAudio}
            isSelecting={isSelectingAudio}
          />
        )}

        {step.content && step.step_type !== 'image' && step.step_type !== 'video' && step.step_type !== 'audio' && (
          <div className="mb-6 bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
            <div className="text-sm text-gray-700">
              <StepContentRenderer stepType={step.step_type} content={step.content} />
            </div>
          </div>
        )}

        {step.status === 'in_progress' && (
          <div className="flex flex-col items-center py-8">
            <Loader2 className="h-12 w-12 animate-spin text-purple-600 mb-4" />
            <p className="text-gray-600">Generating...</p>
          </div>
        )}

        {step.status === 'awaiting_approval' && step.step_type !== 'audio' && (
          <div className="space-y-4">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              rows={2}
              placeholder="Feedback (optional)..."
            />
            <div className="flex space-x-3">
              <button
                onClick={() => onApprove(true, feedback)}
                disabled={isApproving}
                className="flex-1 flex items-center justify-center px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition disabled:opacity-50"
              >
                <ThumbsUp className="h-5 w-5 mr-2" />
                Approve
              </button>
              <button
                onClick={() => onApprove(false, feedback)}
                disabled={isApproving || !!regeneratingStep}
                className="flex-1 flex items-center justify-center px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
              >
                <RotateCcw className="h-5 w-5 mr-2" />
                {regeneratingStep === step.step_type ? 'Regenerating...' : 'Regenerate'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Audio Variant Selection
function AudioVariantSelection({
  audioVariants,
  selectedAudioVariant,
  setSelectedAudioVariant,
  onSelect,
  isSelecting
}: {
  audioVariants: string[]
  selectedAudioVariant: number | null
  setSelectedAudioVariant: (v: number | null) => void
  onSelect: (idx: number) => void
  isSelecting: boolean
}) {
  return (
    <div className="mb-6">
      <div className="flex border-b border-gray-200 mb-4">
        {audioVariants.map((_, index) => (
          <button
            key={index}
            onClick={() => setSelectedAudioVariant(index)}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              (selectedAudioVariant ?? 0) === index
                ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Volume2 className="h-4 w-4 inline mr-1" />
            Вариант {index + 1}
          </button>
        ))}
      </div>
      <div className="flex justify-center mb-4">
        <div className="w-full max-w-sm">
          <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
            <video
              key={selectedAudioVariant ?? 0}
              src={audioVariants[selectedAudioVariant ?? 0]}
              controls
              autoPlay
              className="w-full h-full object-contain"
            />
          </div>
        </div>
      </div>
      <div className="flex justify-center">
        <button
          onClick={() => onSelect(selectedAudioVariant ?? 0)}
          disabled={isSelecting}
          className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition disabled:opacity-50 flex items-center"
        >
          {isSelecting ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Сохранение...
            </>
          ) : (
            <>
              <CheckCircle className="h-5 w-5 mr-2" />
              Выбрать вариант {(selectedAudioVariant ?? 0) + 1}
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// Failed Step Card
function FailedStepCard({
  step,
  stepIndex,
  video,
  videoId,
  regeneratingStep,
  customPrompts,
  onPromptChange,
  onRegenerate
}: {
  step: WorkflowStep
  stepIndex: number
  video: Video
  videoId: number
  regeneratingStep: string | null
  customPrompts: Record<string, CustomPrompt | null>
  onPromptChange: (stepType: string, prompt: CustomPrompt | null) => void
  onRegenerate: () => void
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-red-200 overflow-hidden">
      <div className="bg-red-50 p-4 border-b">
        <div className="flex items-center space-x-3">
          <XCircle className="h-6 w-6 text-red-500" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              Step {stepIndex + 1}: {getStepLabel(step.step_type)}
            </h2>
            <p className="text-sm text-red-600">Failed - click to regenerate</p>
          </div>
        </div>
      </div>
      <div className="p-6 space-y-4">
        {step.content && (
          <div className="bg-gray-50 rounded-lg p-4 max-h-40 overflow-y-auto">
            <div className="text-sm text-gray-600">
              <StepContentRenderer stepType={step.step_type} content={step.content} />
            </div>
          </div>
        )}

        {['story', 'description', 'prompt', 'scenario', 'adaptation'].includes(step.step_type) && (
          <PromptEditor
            videoId={videoId}
            stepType={step.step_type as 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'}
            context={getPromptContext(step.step_type, video)}
            onPromptChange={(customPrompt) => onPromptChange(step.step_type, customPrompt)}
            disabled={!!regeneratingStep}
          />
        )}

        <button
          onClick={onRegenerate}
          disabled={!!regeneratingStep}
          className="w-full flex items-center justify-center px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition disabled:opacity-50"
        >
          {regeneratingStep === step.step_type ? (
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          ) : (
            <RotateCcw className="h-5 w-5 mr-2" />
          )}
          {regeneratingStep === step.step_type ? 'Regenerating...' : `Regenerate ${getStepLabel(step.step_type)}`}
          {customPrompts[step.step_type] && (
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
              <Edit2 className="h-3 w-3 mr-1" />
              Custom
            </span>
          )}
        </button>
      </div>
    </div>
  )
}

// Pending Step Card
function PendingStepCard({
  step,
  video,
  videoId,
  regeneratingStep,
  customPrompts,
  editedImagePrompt,
  setEditedImagePrompt,
  editedVideoPrompt,
  setEditedVideoPrompt,
  onPromptChange,
  onGenerate
}: {
  step: WorkflowStep
  video: Video
  videoId: number
  regeneratingStep: string | null
  customPrompts: Record<string, CustomPrompt | null>
  editedImagePrompt: { main_prompt: string; negative_prompt: string; style_suffix: string } | null
  setEditedImagePrompt: (v: any) => void
  editedVideoPrompt: { motion_prompt: string } | null
  setEditedVideoPrompt: (v: any) => void
  onPromptChange: (stepType: string, prompt: CustomPrompt | null) => void
  onGenerate: () => void
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Next: {getStepLabel(step.step_type)}</h3>
          <p className="text-sm text-gray-500">
            {regeneratingStep === step.step_type ? 'Generating...' : 'Ready to generate'}
          </p>
        </div>
      </div>

      {['story', 'description', 'prompt', 'scenario', 'adaptation'].includes(step.step_type) && (
        <PromptEditor
          videoId={videoId}
          stepType={step.step_type as 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'}
          context={getPromptContext(step.step_type, video)}
          onPromptChange={(customPrompt) => onPromptChange(step.step_type, customPrompt)}
          disabled={!!regeneratingStep}
        />
      )}

      {step.step_type === 'image' && video.prompt_data && (
        <ImagePromptEditor
          promptData={video.prompt_data}
          editedPrompt={editedImagePrompt}
          setEditedPrompt={setEditedImagePrompt}
          disabled={!!regeneratingStep}
        />
      )}

      {step.step_type === 'video' && video.scenario_data && (
        <VideoPromptEditor
          scenarioData={video.scenario_data}
          editedPrompt={editedVideoPrompt}
          setEditedPrompt={setEditedVideoPrompt}
          disabled={!!regeneratingStep}
        />
      )}

      <button
        onClick={onGenerate}
        disabled={!!regeneratingStep}
        className="w-full flex items-center justify-center px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
      >
        {regeneratingStep === step.step_type ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Play className="h-4 w-4 mr-2" />
        )}
        {regeneratingStep === step.step_type ? 'Generating...' : 'Generate'}
        {(customPrompts[step.step_type] ||
          (step.step_type === 'image' && editedImagePrompt) ||
          (step.step_type === 'video' && editedVideoPrompt)) && (
          <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
            <Edit2 className="h-3 w-3 mr-1" />
            Custom Prompt
          </span>
        )}
      </button>
    </div>
  )
}

// Helper function
function getPromptContext(stepType: string, video: Video) {
  switch (stepType) {
    case 'description':
      return { story_data: video.story_data }
    case 'prompt':
      return { description_data: video.description_data }
    case 'scenario':
      return { image_url: video.image_url, description_data: video.description_data }
    case 'adaptation':
      return { scenario_data: video.scenario_data, platforms: video.project?.platforms }
    default:
      return undefined
  }
}

// AUTO mode progress display
const DISCOVER_STEPS = ['story', 'description', 'prompt', 'image', 'scenario', 'video', 'audio']
const REMIX_STEPS = ['image', 'video', 'audio']

function AutoProgressView({
  video,
  steps
}: {
  video: Video
  steps: WorkflowStep[]
}) {
  const isRemix = video.project?.project_type === 'remix'
  const baseSteps = isRemix ? REMIX_STEPS : DISCOVER_STEPS
  // Filter out audio step if audio_mode is 'none'
  const allSteps = video.project?.audio_mode === 'none'
    ? baseSteps.filter(s => s !== 'audio')
    : baseSteps
  const currentStepType = video.current_step?.toLowerCase()

  // Build status map from completed workflow steps
  const stepStatusMap = new Map<string, 'completed' | 'in_progress' | 'pending'>()

  for (const step of steps) {
    const status = step.status?.toLowerCase()
    if (status === 'approved' || status === 'completed') {
      stepStatusMap.set(step.step_type, 'completed')
    }
  }

  // Mark current step as in_progress
  if (currentStepType && allSteps.includes(currentStepType)) {
    stepStatusMap.set(currentStepType, 'in_progress')
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-purple-200 overflow-hidden">
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 border-b">
        <div className="flex items-center space-x-3">
          <Loader2 className="h-6 w-6 text-purple-600 animate-spin" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">Generating Video</h2>
            <p className="text-sm text-gray-600">
              {currentStepType ? `Processing: ${getStepLabel(currentStepType)}` : 'Starting workflow...'}
            </p>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="space-y-3">
          {allSteps.map((stepType, index) => {
            const status = stepStatusMap.get(stepType) || 'pending'
            const isCompleted = status === 'completed'
            const isCurrent = status === 'in_progress'

            return (
              <div
                key={stepType}
                className={`flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  isCurrent ? 'bg-purple-50 border border-purple-200' :
                  isCompleted ? 'bg-green-50' : 'bg-gray-50'
                }`}
              >
                <div className="flex-shrink-0">
                  {isCompleted ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : isCurrent ? (
                    <Loader2 className="h-5 w-5 text-purple-600 animate-spin" />
                  ) : (
                    <Circle className="h-5 w-5 text-gray-300" />
                  )}
                </div>
                <span className="text-sm text-gray-500 w-8">#{index + 1}</span>
                <span className={`flex-1 font-medium ${
                  isCurrent ? 'text-purple-700' :
                  isCompleted ? 'text-green-700' : 'text-gray-400'
                }`}>
                  {getStepLabel(stepType)}
                </span>
                {isCurrent && (
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
