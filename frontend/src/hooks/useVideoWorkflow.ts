import { useState } from 'react'
import { useMutation, useQueryClient } from 'react-query'
import { videosApi, workflowApi, CustomPrompt } from '@/services/api'
import type { Video } from '@/types'

interface EditedImagePrompt {
  main_prompt: string
  negative_prompt: string
  style_suffix: string
}

interface EditedVideoPrompt {
  motion_prompt: string
}

export function useVideoWorkflow(videoId: number, video: Video | undefined) {
  const queryClient = useQueryClient()

  const [feedback, setFeedback] = useState('')
  const [selectedAudioVariant, setSelectedAudioVariant] = useState<number | null>(null)
  const [regeneratingStep, setRegeneratingStep] = useState<string | null>(null)
  const [customPrompts, setCustomPrompts] = useState<Record<string, CustomPrompt | null>>({})
  const [editedImagePrompt, setEditedImagePrompt] = useState<EditedImagePrompt | null>(null)
  const [editedVideoPrompt, setEditedVideoPrompt] = useState<EditedVideoPrompt | null>(null)

  const handlePromptChange = (stepType: string, customPrompt: CustomPrompt | null) => {
    setCustomPrompts(prev => ({ ...prev, [stepType]: customPrompt }))
  }

  // Auto-generate mutation
  const autoGenerateMutation = useMutation(
    () => workflowApi.autoGenerateToVideo(videoId),
    {
      onSuccess: () => queryClient.invalidateQueries(['video', videoId]),
      onError: (error) => console.error('Auto-generation failed:', error)
    }
  )

  // Delete mutation
  const deleteMutation = useMutation(
    () => videosApi.delete(videoId),
    { onSuccess: () => {} } // Navigation handled in component
  )

  // Toggle workflow mode mutation
  const toggleWorkflowModeMutation = useMutation(
    () => videosApi.update(videoId, {
      workflow_mode: video?.workflow_mode === 'MANUAL' ? 'AUTO' : 'MANUAL'
    }),
    { onSuccess: () => queryClient.invalidateQueries(['video', videoId]) }
  )

  // Approve step mutation
  const approveStepMutation = useMutation(
    ({ stepId, approved, feedback: fb }: { stepId: number; approved: boolean; feedback?: string; stepType?: string }) =>
      workflowApi.approveStep(stepId, approved, fb),
    {
      onSuccess: (data, variables) => {
        setFeedback('')
        queryClient.invalidateQueries(['video', videoId])
        if (data.data?.continue_workflow) {
          autoGenerateMutation.mutate()
        }
        if (!variables.approved && variables.stepType) {
          setTimeout(() => {
            handleRegenerateStep(variables.stepType!)
          }, 100)
        }
      }
    }
  )

  // Select audio variant mutation
  const selectAudioMutation = useMutation(
    (variantIndex: number) => workflowApi.selectAudioVariant(videoId, variantIndex),
    {
      onSuccess: () => {
        setSelectedAudioVariant(null)
        queryClient.invalidateQueries(['video', videoId])
      },
      onError: (error) => console.error('Audio selection failed:', error)
    }
  )

  // Regenerate step
  const handleRegenerateStep = async (stepType: string) => {
    if (!video || regeneratingStep) return
    const getStepContent = (type: string) => video.workflow_steps?.find(s => s.step_type === type)?.content
    const customPrompt = customPrompts[stepType] || undefined

    setRegeneratingStep(stepType)
    try {
      switch (stepType) {
        case 'story': {
          const project = video.project
          await workflowApi.generateStory(videoId, {
            theme: project?.story_template || '',
            duration: project?.duration || 5,
            platforms: project?.platforms || [],
            custom_prompt: customPrompt
          })
          break
        }
        case 'description': {
          const storyData = video.story_data || getStepContent('story')
          if (storyData) await workflowApi.generateDescription(videoId, storyData, customPrompt)
          break
        }
        case 'prompt': {
          const descriptionData = video.description_data || getStepContent('description')
          if (descriptionData) await workflowApi.generatePrompt(videoId, descriptionData, customPrompt)
          break
        }
        case 'image': {
          const originalPromptData = video.prompt_data || getStepContent('prompt')
          const aspectRatio = video.project?.aspect_ratio || '9:16'
          const isRemix = video.project?.project_type === 'remix'

          if (isRemix && !editedImagePrompt) {
            await workflowApi.generateImage(videoId, '', aspectRatio, 'std', true)
          } else if (!originalPromptData && video.image_prompt) {
            const prompt = editedImagePrompt?.main_prompt || video.image_prompt
            await workflowApi.generateImage(videoId, prompt, aspectRatio)
          } else if (originalPromptData || editedImagePrompt) {
            const promptData = editedImagePrompt ? {
              ...originalPromptData,
              main_prompt: editedImagePrompt.main_prompt,
              negative_prompt: editedImagePrompt.negative_prompt,
              style_suffix: editedImagePrompt.style_suffix
            } : originalPromptData
            if (promptData) await workflowApi.generateImage(videoId, promptData, aspectRatio)
          }
          setEditedImagePrompt(null)
          break
        }
        case 'scenario': {
          const imageUrl = video.image_url
          const descriptionData = video.description_data || getStepContent('description')
          if (imageUrl && descriptionData) await workflowApi.generateScenario(videoId, imageUrl, descriptionData, customPrompt)
          break
        }
        case 'video': {
          const imageUrl = video.image_url
          const originalScenarioData = video.scenario_data || getStepContent('scenario')
          const scenarioData = editedVideoPrompt ? {
            ...originalScenarioData,
            motion_prompt: editedVideoPrompt.motion_prompt
          } : originalScenarioData
          if (imageUrl && scenarioData) await workflowApi.generateVideo(videoId, imageUrl, scenarioData)
          setEditedVideoPrompt(null)
          break
        }
        case 'adaptation': {
          const scenarioData = video.scenario_data || getStepContent('scenario')
          const platforms = video.project?.platforms
          if (scenarioData && platforms) await workflowApi.adaptForPlatforms(videoId, scenarioData, platforms, customPrompt)
          break
        }
        case 'audio': {
          await workflowApi.generateAudio(videoId)
          break
        }
      }
      setCustomPrompts(prev => ({ ...prev, [stepType]: null }))
      queryClient.invalidateQueries(['video', videoId])
    } catch (error) {
      console.error('Failed to regenerate step:', error)
    } finally {
      setRegeneratingStep(null)
    }
  }

  return {
    // State
    feedback,
    setFeedback,
    selectedAudioVariant,
    setSelectedAudioVariant,
    regeneratingStep,
    customPrompts,
    editedImagePrompt,
    setEditedImagePrompt,
    editedVideoPrompt,
    setEditedVideoPrompt,

    // Handlers
    handlePromptChange,
    handleRegenerateStep,

    // Mutations
    autoGenerateMutation,
    deleteMutation,
    toggleWorkflowModeMutation,
    approveStepMutation,
    selectAudioMutation
  }
}
