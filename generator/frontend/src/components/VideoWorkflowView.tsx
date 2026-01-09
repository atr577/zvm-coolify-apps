import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from 'react-query'
import { WorkflowStep, Video } from '@/types'
import { ChevronDown, ChevronRight, CheckCircle, Clock, XCircle, ThumbsUp, ThumbsDown, RotateCcw, Play, Edit2 } from 'lucide-react'
import { workflowApi, CustomPrompt } from '@/services/api'
import PromptEditor from './PromptEditor'

interface VideoWorkflowViewProps {
  steps: WorkflowStep[]
  videoId: number
  video?: Video
  onStepApproved?: (stepId: number) => void
  onRegenerateStep?: (stepType: string, customPrompt?: CustomPrompt) => void
}

export default function VideoWorkflowView({ steps, videoId, video, onStepApproved, onRegenerateStep }: VideoWorkflowViewProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({})
  const [feedback, setFeedback] = useState<Record<number, string>>({})
  const [lastApprovedStepId, setLastApprovedStepId] = useState<number | null>(null)
  const [customPrompts, setCustomPrompts] = useState<Record<string, CustomPrompt | null>>({})
  const queryClient = useQueryClient()

  // Handle custom prompt changes from PromptEditor
  const handlePromptChange = (stepType: string, customPrompt: CustomPrompt | null) => {
    setCustomPrompts(prev => ({ ...prev, [stepType]: customPrompt }))
  }

  // Get context for prompt preview based on step type
  const getPromptContext = (stepType: string): Record<string, any> | undefined => {
    if (!video) return undefined

    switch (stepType) {
      case 'description':
        return { story_data: video.story_data }
      case 'prompt':
        return { description_data: video.description_data }
      case 'scenario':
        return {
          image_url: video.image_url,
          description_data: video.description_data
        }
      case 'adaptation':
        return {
          scenario_data: video.scenario_data,
          platforms: video.project?.platforms
        }
      default:
        return undefined
    }
  }

  // Auto-expand next step after approval
  useEffect(() => {
    if (lastApprovedStepId !== null) {
      const currentIndex = steps.findIndex(s => s.id === lastApprovedStepId)
      if (currentIndex >= 0 && currentIndex < steps.length - 1) {
        const nextStep = steps[currentIndex + 1]
        setExpandedSteps(prev => ({ ...prev, [nextStep.id]: true }))
      }
      setLastApprovedStepId(null)
    }
  }, [steps, lastApprovedStepId])

  // Auto-expand steps with awaiting_approval status
  useEffect(() => {
    const awaitingApprovalSteps = steps.filter(s => s.status === 'awaiting_approval')
    if (awaitingApprovalSteps.length > 0) {
      const newExpandedSteps: Record<number, boolean> = {}
      awaitingApprovalSteps.forEach(step => {
        newExpandedSteps[step.id] = true
      })
      setExpandedSteps(prev => ({ ...prev, ...newExpandedSteps }))
    }
  }, [steps.length, steps.map(s => `${s.id}-${s.status}`).join(',')])

  const toggleStep = (stepId: number) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepId]: !prev[stepId]
    }))
  }

  // Approve/Reject step mutation
  const approveStepMutation = useMutation(
    ({ stepId, approved, feedback }: { stepId: number; approved: boolean; feedback?: string }) =>
      workflowApi.approveStep(stepId, approved, feedback),
    {
      onSuccess: (_, variables) => {
        setFeedback(prev => ({ ...prev, [variables.stepId]: '' }))

        // Mark step for auto-expansion after data refresh
        if (variables.approved) {
          setLastApprovedStepId(variables.stepId)
          if (onStepApproved) {
            onStepApproved(variables.stepId)
          }
        }

        queryClient.invalidateQueries(['video', videoId])
      },
    }
  )

  // Restart step mutation (resets IN_PROGRESS or FAILED to PENDING)
  const restartStepMutation = useMutation(
    (stepId: number) => workflowApi.approveStep(stepId, false, '', true),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['video', videoId])
      },
    }
  )

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
      case 'rejected':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'in_progress':
        return <Clock className="h-5 w-5 text-yellow-500 animate-pulse" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  const getStepLabel = (stepType: string) => {
    const map: Record<string, string> = {
      story: 'Story',
      description: 'Scene',
      prompt: 'First shot',
      image: 'First shot preview',
      scenario: 'Scenario',
      video: 'Video',
      adaptation: 'Meta for platforms',
      publishing: 'Publishing'
    }
    return map[stepType] || stepType
  }

  return (
    <div className="space-y-2">
      {steps.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Нет этапов workflow для отображения
        </div>
      )}

      {steps.map((step, index) => {
        const isExpanded = expandedSteps[step.id] || false

        return (
          <div key={step.id} className="bg-white border rounded-lg">
            {/* Header */}
            <div
              onClick={() => toggleStep(step.id)}
              className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
            >
              <div className="flex items-center space-x-3 flex-1">
                <button>
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-500" />
                  )}
                </button>

                <span className="text-sm font-medium text-gray-500">
                  Step {index + 1}:
                </span>

                <h4 className="font-semibold text-gray-900">
                  {getStepLabel(step.step_type)}
                </h4>

                {getStatusIcon(step.status)}

                <span className="text-sm text-gray-600 capitalize">
                  {step.status.replace('_', ' ')}
                </span>
              </div>

              {step.generation_time_seconds && (
                <span className="text-xs text-gray-500">
                  {step.generation_time_seconds.toFixed(1)}s
                </span>
              )}
            </div>

            {/* Expanded content */}
            {isExpanded && (
              <div className="px-4 pb-4 border-t space-y-3 mt-2">
                {/* Prompt tracking info */}
                {step.prompt_manually_edited && (
                  <div className="flex items-center space-x-2 text-sm bg-yellow-50 p-2 rounded">
                    <Edit2 className="h-4 w-4 text-yellow-600" />
                    <span className="text-yellow-800 font-medium">
                      Generated with custom prompt
                    </span>
                  </div>
                )}

                {/* Show original or custom prompt if available */}
                {(step.custom_prompt || step.original_prompt) && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      {step.prompt_manually_edited ? 'Custom Prompt Used:' : 'Prompt Used:'}
                    </h5>
                    <div className="space-y-2">
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase">System:</span>
                        <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto whitespace-pre-wrap max-h-24">
                          {(step.custom_prompt || step.original_prompt)?.system_prompt}
                        </pre>
                      </div>
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase">User:</span>
                        <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto whitespace-pre-wrap max-h-48">
                          {(step.custom_prompt || step.original_prompt)?.user_prompt}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}

                {/* Legacy prompt_used field */}
                {step.prompt_used && !step.original_prompt && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Промпт:
                    </h5>
                    <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto whitespace-pre-wrap">
                      {step.prompt_used}
                    </pre>
                  </div>
                )}

                {/* Content result */}
                {step.content && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Результат:
                    </h5>
                    {/* Render image for image steps */}
                    {step.step_type === 'image' && step.content.image_url && (
                      <div className="mb-3">
                        <img
                          src={step.content.image_url}
                          alt="Generated preview"
                          className="max-w-full h-auto rounded-lg border"
                          style={{ maxHeight: '400px' }}
                        />
                      </div>
                    )}
                    {/* Render video for video steps */}
                    {step.step_type === 'video' && step.content.video_url && (
                      <div className="mb-3">
                        <video
                          src={step.content.video_url}
                          controls
                          className="max-w-full h-auto rounded-lg border"
                          style={{ maxHeight: '400px' }}
                        />
                      </div>
                    )}
                    {/* Show JSON for other content types */}
                    {step.step_type !== 'image' && step.step_type !== 'video' && (
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto max-h-64">
                        {JSON.stringify(step.content, null, 2)}
                      </pre>
                    )}
                  </div>
                )}

                {/* User feedback */}
                {step.user_feedback && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Фидбек пользователя:
                    </h5>
                    <p className="text-sm text-gray-600 bg-yellow-50 p-3 rounded">
                      {step.user_feedback}
                    </p>
                  </div>
                )}

                {/* Validation info */}
                {step.user_approved !== null && (
                  <div className="flex items-center space-x-2 text-sm">
                    <span className="font-semibold text-gray-700">Одобрено пользователем:</span>
                    <span className={step.user_approved ? 'text-green-600' : 'text-red-600'}>
                      {step.user_approved ? '✓ Да' : '✗ Нет'}
                    </span>
                  </div>
                )}

                {/* Validation attempts */}
                {step.validation_attempts > 0 && (
                  <div className="text-sm text-gray-600">
                    Попыток валидации: {step.validation_attempts} / {step.max_validation_attempts}
                  </div>
                )}

                {/* Reset button for in_progress or failed steps */}
                {(step.status === 'in_progress' || step.status === 'failed') && (
                  <div className="pt-3 border-t">
                    <button
                      onClick={() => restartStepMutation.mutate(step.id)}
                      disabled={restartStepMutation.isLoading}
                      className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition disabled:opacity-50"
                    >
                      <RotateCcw className="h-4 w-4 mr-2" />
                      Reset Step
                    </button>
                    {step.status === 'failed' && (
                      <p className="mt-2 text-sm text-red-600">
                        Step failed. Click to reset and try again.
                      </p>
                    )}
                  </div>
                )}

                {/* Generate button for pending steps (when previous step is approved) */}
                {step.status === 'pending' && onRegenerateStep && index > 0 && (
                  steps[index - 1]?.status === 'approved' || steps[index - 1]?.status === 'completed'
                ) && (
                  <div className="pt-3 border-t space-y-3">
                    {/* Show PromptEditor for AI-generated steps */}
                    {['story', 'description', 'prompt', 'scenario', 'adaptation'].includes(step.step_type) && (
                      <PromptEditor
                        videoId={videoId}
                        stepType={step.step_type as 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'}
                        context={getPromptContext(step.step_type)}
                        onPromptChange={(customPrompt) => handlePromptChange(step.step_type, customPrompt)}
                      />
                    )}
                    <button
                      onClick={() => onRegenerateStep(step.step_type, customPrompts[step.step_type] || undefined)}
                      className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 transition"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Generate {getStepLabel(step.step_type)}
                      {customPrompts[step.step_type] && (
                        <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-yellow-200 text-yellow-800">
                          <Edit2 className="h-3 w-3 mr-0.5" />
                          Custom
                        </span>
                      )}
                    </button>
                  </div>
                )}

                {/* Approve/Reject controls */}
                {step.status === 'awaiting_approval' && (
                  <div className="pt-3 border-t space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Комментарий (опционально):
                      </label>
                      <textarea
                        value={feedback[step.id] || ''}
                        onChange={(e) => setFeedback(prev => ({ ...prev, [step.id]: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
                        rows={2}
                        placeholder="Что нужно изменить?"
                      />
                    </div>

                    <div className="flex space-x-3">
                      <button
                        onClick={() => approveStepMutation.mutate({
                          stepId: step.id,
                          approved: true,
                          feedback: feedback[step.id]
                        })}
                        disabled={approveStepMutation.isLoading}
                        className="flex-1 flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition disabled:opacity-50"
                      >
                        <ThumbsUp className="h-4 w-4 mr-2" />
                        Approve
                      </button>

                      <button
                        onClick={() => approveStepMutation.mutate({
                          stepId: step.id,
                          approved: false,
                          feedback: feedback[step.id]
                        })}
                        disabled={approveStepMutation.isLoading}
                        className="flex-1 flex items-center justify-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition disabled:opacity-50"
                      >
                        <ThumbsDown className="h-4 w-4 mr-2" />
                        Reject & Regenerate
                      </button>
                    </div>
                  </div>
                )}

                {/* Timestamps */}
                <div className="flex flex-wrap gap-4 text-xs text-gray-500 pt-2 border-t">
                  {step.started_at && (
                    <span>Начало: {new Date(step.started_at).toLocaleString()}</span>
                  )}
                  {step.completed_at && (
                    <span>Завершено: {new Date(step.completed_at).toLocaleString()}</span>
                  )}
                  <span>Создано: {new Date(step.created_at).toLocaleString()}</span>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
