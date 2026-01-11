/**
 * Workflow V3 Hook - Simple step-by-step workflow management
 *
 * Provides:
 * - generateStep(step) - Generate one step
 * - selectVariant(variantId) - Select a variant
 * - runAuto() - Run all steps automatically
 * - getVariants(step) - Get all variants for a step
 */
import { useState, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from 'react-query'
import { workflowApi, StepType } from '@/services/api'

// Steps configuration: unified 4-step workflow
// scenario generates image_prompt + motion_prompt from story_template + content_variables
export const DISCOVER_STEPS = ['scenario', 'image', 'video', 'audio'] as const
export const REMIX_STEPS = ['image', 'video', 'audio'] as const

export type { StepType }

export function useWorkflowV3(videoId: number, isRemix: boolean = false, includeAudio: boolean = true) {
  const queryClient = useQueryClient()
  const baseSteps = isRemix ? REMIX_STEPS : DISCOVER_STEPS
  const steps = includeAudio ? baseSteps : baseSteps.filter(s => s !== 'audio')

  // Current step being generated
  const [generatingStep, setGeneratingStep] = useState<string | null>(null)

  // Error state
  const [error, setError] = useState<string | null>(null)

  // Generate step mutation
  const generateStepMutation = useMutation(
    ({ step, feedback }: { step: StepType; feedback?: string }) =>
      workflowApi.generateStep(videoId, step, feedback),
    {
      onMutate: ({ step }) => {
        setGeneratingStep(step)
        setError(null)
      },
      onSuccess: async (_res, { step }) => {
        await queryClient.invalidateQueries(['video', videoId])
        await queryClient.invalidateQueries(['variants', videoId, step])
        setGeneratingStep(null)
      },
      onError: (err: Error) => {
        setError(err.message)
        setGeneratingStep(null)
      },
    }
  )

  // Switch variant mutation (for preview, no auto-continue)
  const switchVariantMutation = useMutation(
    (variantId: number) => workflowApi.switchVariant(videoId, variantId),
    {
      onSuccess: async (res) => {
        await queryClient.invalidateQueries(['video', videoId])
        await queryClient.invalidateQueries(['variants', videoId, res.data.step_type])
      },
      onError: (err: Error) => {
        setError(err.message)
      },
    }
  )

  // Approve variant mutation (move to next step)
  const approveVariantMutation = useMutation(
    (variantId: number) => workflowApi.approveVariant(videoId, variantId),
    {
      onSuccess: (res) => {
        queryClient.invalidateQueries(['video', videoId])
        // Invalidate stale steps variants
        res.data.stale_steps.forEach((step: string) => {
          queryClient.invalidateQueries(['variants', videoId, step])
        })
      },
      onError: (err: Error) => {
        setError(err.message)
      },
    }
  )

  // Legacy alias
  const selectVariantMutation = approveVariantMutation

  // Run auto mutation
  const runAutoMutation = useMutation(
    () => workflowApi.runAuto(videoId),
    {
      onMutate: () => {
        setError(null)
      },
      onSuccess: () => {
        queryClient.invalidateQueries(['video', videoId])
      },
      onError: (err: Error) => {
        setError(err.message)
      },
    }
  )

  // Update content mutation (manual edit)
  const updateContentMutation = useMutation(
    ({ step, content }: { step: StepType; content: Record<string, unknown> }) =>
      workflowApi.updateContent(videoId, step, content),
    {
      onSuccess: async (_res, { step }) => {
        await queryClient.invalidateQueries(['video', videoId])
        await queryClient.invalidateQueries(['variants', videoId, step])
      },
      onError: (err: Error) => {
        setError(err.message)
      },
    }
  )

  // Go to step mutation (back navigation)
  const gotoStepMutation = useMutation(
    (step: StepType) => workflowApi.gotoStep(videoId, step),
    {
      onSuccess: async () => {
        await queryClient.invalidateQueries(['video', videoId])
      },
      onError: (err: Error) => {
        setError(err.message)
      },
    }
  )

  // Get variants for a step (query)
  const useVariants = (step: StepType) => {
    return useQuery(
      ['variants', videoId, step],
      () => workflowApi.getVariants(videoId, step).then((res) => res.data),
      { enabled: !!step }
    )
  }

  // Generate step
  const generateStep = useCallback(
    (step: StepType, feedback?: string) => {
      generateStepMutation.mutate({ step, feedback })
    },
    [generateStepMutation]
  )

  // Switch variant (for preview)
  const switchVariant = useCallback(
    (variantId: number) => {
      switchVariantMutation.mutate(variantId)
    },
    [switchVariantMutation]
  )

  // Approve variant (move to next step)
  const approveVariant = useCallback(
    (variantId: number) => {
      approveVariantMutation.mutate(variantId)
    },
    [approveVariantMutation]
  )

  // Go to step (back navigation)
  const gotoStep = useCallback(
    (step: StepType) => {
      gotoStepMutation.mutate(step)
    },
    [gotoStepMutation]
  )

  // Legacy alias
  const selectVariant = approveVariant

  // Run all steps automatically
  const runAuto = useCallback(() => {
    runAutoMutation.mutate()
  }, [runAutoMutation])

  // Update content (manual edit)
  const updateContent = useCallback(
    (step: StepType, content: Record<string, unknown>) => {
      updateContentMutation.mutate({ step, content })
    },
    [updateContentMutation]
  )

  // Clear error
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    // State
    steps,
    generatingStep,
    error,
    isGenerating: !!generatingStep || runAutoMutation.isLoading,
    isRunningAuto: runAutoMutation.isLoading,

    // Actions
    generateStep,
    switchVariant,
    approveVariant,
    gotoStep,
    selectVariant, // Legacy alias for approveVariant
    runAuto,
    updateContent,
    clearError,
    useVariants,

    // Mutation states
    generateStepMutation,
    switchVariantMutation,
    approveVariantMutation,
    gotoStepMutation,
    selectVariantMutation, // Legacy alias
    runAutoMutation,
    updateContentMutation,
  }
}
