import { useState, useEffect } from 'react'
import { useMutation } from 'react-query'
import { Edit2, RotateCcw, Check, X, AlertCircle } from 'lucide-react'
import { workflowApi, PreviewPromptRequest, CustomPrompt } from '@/services/api'

interface PromptEditorProps {
  videoId: number
  stepType: 'story' | 'description' | 'prompt' | 'scenario' | 'adaptation'
  context?: Record<string, any>
  onPromptChange?: (customPrompt: CustomPrompt | null) => void
  disabled?: boolean
}

export default function PromptEditor({
  videoId,
  stepType,
  context,
  onPromptChange,
  disabled = false
}: PromptEditorProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [userPrompt, setUserPrompt] = useState('')
  const [originalSystemPrompt, setOriginalSystemPrompt] = useState('')
  const [originalUserPrompt, setOriginalUserPrompt] = useState('')
  const [isModified, setIsModified] = useState(false)

  // Preview prompt mutation
  const previewMutation = useMutation(
    (request: PreviewPromptRequest) => workflowApi.previewPrompt(request),
    {
      onSuccess: (response) => {
        const data = response.data
        setSystemPrompt(data.system_prompt)
        setUserPrompt(data.user_prompt)
        setOriginalSystemPrompt(data.system_prompt)
        setOriginalUserPrompt(data.user_prompt)
        setIsModified(false)
      }
    }
  )

  // Load prompt preview on mount
  useEffect(() => {
    previewMutation.mutate({
      video_id: videoId,
      step_type: stepType,
      context
    })
  }, [videoId, stepType])

  // Check if prompts are modified
  useEffect(() => {
    const modified =
      systemPrompt !== originalSystemPrompt ||
      userPrompt !== originalUserPrompt
    setIsModified(modified)

    // Notify parent of changes
    if (onPromptChange) {
      if (modified) {
        onPromptChange({
          system_prompt: systemPrompt,
          user_prompt: userPrompt
        })
      } else {
        onPromptChange(null)
      }
    }
  }, [systemPrompt, userPrompt, originalSystemPrompt, originalUserPrompt])

  // Reset to original
  const handleReset = () => {
    setSystemPrompt(originalSystemPrompt)
    setUserPrompt(originalUserPrompt)
    setIsEditing(false)
  }

  // Apply changes
  const handleApply = () => {
    setIsEditing(false)
  }

  // Cancel editing
  const handleCancel = () => {
    setSystemPrompt(originalSystemPrompt)
    setUserPrompt(originalUserPrompt)
    setIsEditing(false)
  }

  const getStepLabel = () => {
    const labels: Record<string, string> = {
      story: 'Story Generation',
      description: 'Scene Description',
      prompt: 'Image Prompt',
      scenario: 'Video Scenario',
      adaptation: 'Platform Adaptation'
    }
    return labels[stepType] || stepType
  }

  return (
    <div className="border rounded-lg bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
        <span className="text-sm font-medium text-gray-700">
          Prompt for {getStepLabel()}
        </span>
        {isModified && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
            <Edit2 className="h-3 w-3 mr-1" />
            Modified
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-3 space-y-4">
        {/* Loading state */}
        {previewMutation.isLoading && (
          <div className="text-center py-4 text-gray-500">
            Loading prompt...
          </div>
        )}

        {/* Error state */}
        {previewMutation.isError && (
          <div className="flex items-center space-x-2 text-red-600 bg-red-50 p-3 rounded">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">Failed to load prompt. Please try again.</span>
          </div>
        )}

        {/* Prompt display/edit */}
        {!previewMutation.isLoading && !previewMutation.isError && (
          <>
            {/* System Prompt */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-gray-600 uppercase">
                  System Prompt
                </label>
                {!isEditing && (
                  <button
                    onClick={() => setIsEditing(true)}
                    disabled={disabled}
                    className="text-xs text-primary-600 hover:text-primary-700 flex items-center space-x-1 disabled:opacity-50"
                  >
                    <Edit2 className="h-3 w-3" />
                    <span>Edit</span>
                  </button>
                )}
              </div>
              {isEditing ? (
                <textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                  rows={3}
                  disabled={disabled}
                />
              ) : (
                <pre className="text-xs bg-white p-3 rounded border overflow-x-auto whitespace-pre-wrap max-h-24">
                  {systemPrompt}
                </pre>
              )}
            </div>

            {/* User Prompt */}
            <div>
              <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
                User Prompt
              </label>
              {isEditing ? (
                <textarea
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                  rows={12}
                  disabled={disabled}
                />
              ) : (
                <pre className="text-xs bg-white p-3 rounded border overflow-x-auto whitespace-pre-wrap max-h-48">
                  {userPrompt}
                </pre>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-2 border-t">
              {isEditing ? (
                <div className="flex space-x-2">
                  <button
                    onClick={handleApply}
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded hover:bg-primary-700 transition"
                  >
                    <Check className="h-4 w-4 mr-1" />
                    Apply Changes
                  </button>
                  <button
                    onClick={handleCancel}
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition"
                  >
                    <X className="h-4 w-4 mr-1" />
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="text-xs text-gray-500">
                  {isModified ? (
                    <span className="text-yellow-600">
                      Prompt will be used with your modifications
                    </span>
                  ) : (
                    <span>Click "Edit" to modify the prompt</span>
                  )}
                </div>
              )}

              {isModified && !isEditing && (
                <button
                  onClick={handleReset}
                  disabled={disabled}
                  className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition disabled:opacity-50"
                >
                  <RotateCcw className="h-4 w-4 mr-1" />
                  Reset to Original
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
