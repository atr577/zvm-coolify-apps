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
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Add auth token interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Steps configuration (scenario before prompt for better image-animation alignment)
export const DISCOVER_STEPS = ['story', 'description', 'scenario', 'prompt', 'image', 'video', 'audio'] as const
export const REMIX_STEPS = ['image', 'video', 'audio'] as const

export type StepType = typeof DISCOVER_STEPS[number]

export interface Variant {
  id: number
  step_type: string
  content: Record<string, unknown>
  is_selected: boolean
  created_at: string
}

export interface GenerateResponse {
  variant_id: number
  step_type: string
  content: Record<string, unknown>
  is_selected: boolean
}

export interface SelectResponse {
  variant_id: number
  step_type: string
  stale_steps: string[]
}

export interface RunAutoResponse {
  video_id: number
  status: string
  completed_steps: string[]
  current_step: string | null
  error: string | null
}

// V3 API calls
const v3Api = {
  generateStep: (videoId: number, step: string) =>
    api.post<GenerateResponse>(`/api/v3/${videoId}/generate/${step}`),

  getVariants: (videoId: number, step: string) =>
    api.get<{ step_type: string; variants: Variant[]; selected_id: number | null }>(
      `/api/v3/${videoId}/variants/${step}`
    ),

  selectVariant: (videoId: number, variantId: number) =>
    api.post<SelectResponse>(`/api/v3/${videoId}/select/${variantId}`),

  runAuto: (videoId: number) =>
    api.post<RunAutoResponse>(`/api/v3/${videoId}/run-auto`),
}

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
    (step: string) => v3Api.generateStep(videoId, step),
    {
      onMutate: (step: string) => {
        setGeneratingStep(step)
        setError(null)
      },
      onSuccess: (_res, step: string) => {
        queryClient.invalidateQueries(['video', videoId])
        queryClient.invalidateQueries(['variants', videoId, step])
        setGeneratingStep(null)
      },
      onError: (err: Error) => {
        setError(err.message)
        setGeneratingStep(null)
      },
    }
  )

  // Select variant mutation
  const selectVariantMutation = useMutation(
    (variantId: number) => v3Api.selectVariant(videoId, variantId),
    {
      onSuccess: (res: { data: SelectResponse }) => {
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

  // Run auto mutation
  const runAutoMutation = useMutation(
    () => v3Api.runAuto(videoId),
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

  // Get variants for a step (query)
  const useVariants = (step: string) => {
    return useQuery(
      ['variants', videoId, step],
      () => v3Api.getVariants(videoId, step).then((res: { data: { step_type: string; variants: Variant[]; selected_id: number | null } }) => res.data),
      { enabled: !!step }
    )
  }

  // Generate step
  const generateStep = useCallback(
    (step: string) => {
      generateStepMutation.mutate(step)
    },
    [generateStepMutation]
  )

  // Select variant
  const selectVariant = useCallback(
    (variantId: number) => {
      selectVariantMutation.mutate(variantId)
    },
    [selectVariantMutation]
  )

  // Run all steps automatically
  const runAuto = useCallback(() => {
    runAutoMutation.mutate()
  }, [runAutoMutation])

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
    selectVariant,
    runAuto,
    clearError,
    useVariants,

    // Mutation states
    generateStepMutation,
    selectVariantMutation,
    runAutoMutation,
  }
}
