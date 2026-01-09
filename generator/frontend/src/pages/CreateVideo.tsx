import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { ArrowLeft } from 'lucide-react'
import { projectsApi, aiApi, videosApi } from '@/services/api'
import VideoVariantSelector from '@/components/VideoVariantSelector'
import type { ContentVariant, WorkflowMode } from '@/types'

export default function CreateVideo() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = parseInt(projectId || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [variants, setVariants] = useState<ContentVariant[]>([])
  const [excludedVariants, setExcludedVariants] = useState<ContentVariant[]>([])
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode>('AUTO')

  const { data: project } = useQuery(
    ['project', id],
    () => projectsApi.get(id).then(res => res.data)
  )

  // Генерация вариантов
  const generateMutation = useMutation(
    () => aiApi.generateVariants(id),
    {
      onSuccess: (data) => {
        setVariants(data.data.variants)
      },
    }
  )

  const regenerateMutation = useMutation(
    () => aiApi.regenerateVariants(id, excludedVariants),
    {
      onSuccess: (data) => {
        setExcludedVariants([...excludedVariants, ...variants])
        setVariants(data.data.variants)
      },
    }
  )

  // Создание видео
  const createVideoMutation = useMutation(
    (variant: ContentVariant) => {
      const title = variant.description

      return videosApi.create({
        project_id: id,
        title,
        content_variables: variant.content_variables,
        workflow_mode: workflowMode
      })
    },
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['videos', id])
        navigate(`/video/${data.data.id}`)
      },
    }
  )

  // Генерируем варианты при загрузке
  useEffect(() => {
    if (id) {
      generateMutation.mutate()
    }
  }, [id])

  if (!project) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5 mr-2" />
          Назад
        </button>

        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Создание ролика в проекте: {project.name}
        </h1>

        {/* Workflow Mode Selector */}
        <div className="bg-gray-50 p-4 rounded-lg mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Режим генерации:
          </label>
          <div className="flex space-x-4">
            <label className={`flex-1 cursor-pointer p-3 rounded-lg border-2 transition ${
              workflowMode === 'AUTO'
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input
                type="radio"
                name="workflowMode"
                value="auto"
                checked={workflowMode === 'AUTO'}
                onChange={() => setWorkflowMode('AUTO')}
                className="sr-only"
              />
              <div className="font-medium text-gray-900">Auto</div>
              <div className="text-sm text-gray-500">Все шаги автоматически, без остановок</div>
            </label>

            <label className={`flex-1 cursor-pointer p-3 rounded-lg border-2 transition ${
              workflowMode === 'MANUAL'
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input
                type="radio"
                name="workflowMode"
                value="manual"
                checked={workflowMode === 'MANUAL'}
                onChange={() => setWorkflowMode('MANUAL')}
                className="sr-only"
              />
              <div className="font-medium text-gray-900">Manual</div>
              <div className="text-sm text-gray-500">Approve каждого шага, полный контроль</div>
            </label>
          </div>
        </div>
      </div>

      {/* Генерация вариантов */}
      {generateMutation.isLoading && (
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-600">AI анализирует шаблон и генерирует вариации...</p>
          </div>
        </div>
      )}

      {/* Выбор варианта */}
      {!generateMutation.isLoading && variants.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <VideoVariantSelector
            variants={variants}
            onSelect={(variant) => createVideoMutation.mutate(variant)}
            onRegenerate={() => regenerateMutation.mutate()}
            isRegenerating={regenerateMutation.isLoading}
          />
        </div>
      )}

      {/* Ошибка */}
      {generateMutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Ошибка при генерации вариантов. Попробуйте еще раз.
          <button
            onClick={() => generateMutation.mutate()}
            className="ml-4 underline hover:no-underline"
          >
            Повторить
          </button>
        </div>
      )}
    </div>
  )
}
