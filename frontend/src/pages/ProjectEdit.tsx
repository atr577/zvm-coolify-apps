import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { ArrowLeft } from 'lucide-react'
import { projectsApi } from '@/services/api'
import ProjectForm from '@/components/ProjectForm'
import type { CreateProjectDto } from '@/types'

export default function ProjectEdit() {
  const { id } = useParams<{ id: string }>()
  const projectId = parseInt(id || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: project, isLoading } = useQuery(
    ['project', projectId],
    () => projectsApi.get(projectId).then(res => res.data)
  )

  const updateMutation = useMutation(
    (data: CreateProjectDto) => projectsApi.update(projectId, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['project', projectId])
        queryClient.invalidateQueries('projects')
        navigate(`/?project=${projectId}`)
      },
    }
  )

  if (isLoading || !project) {
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
          onClick={() => navigate(`/?project=${projectId}`)}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5 mr-2" />
          Назад к проекту
        </button>

        <h1 className="text-3xl font-bold text-gray-900">
          Редактирование проекта: {project.name}
        </h1>
        <p className="text-sm text-gray-600 mt-2">
          Редактирование шаблона проекта. Изменения повлияют на новые ролики.
        </p>
      </div>

      {/* Form */}
      <div className="bg-white p-6 rounded-lg shadow">
        <ProjectForm
          initialData={{
            ...project,
            description: project.description ?? undefined,
            system_prompts: project.system_prompts ?? undefined
          }}
          onSubmit={(data) => updateMutation.mutate(data)}
          onCancel={() => navigate(`/?project=${projectId}`)}
          isLoading={updateMutation.isLoading}
        />
      </div>
    </div>
  )
}
