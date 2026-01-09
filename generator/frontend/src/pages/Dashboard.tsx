import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { projectsApi, videosApi } from '@/services/api'
import ProjectCard from '@/components/ProjectCard'
import ProjectForm from '@/components/ProjectForm'
import type { Project, Video, CreateProjectDto } from '@/types'

export default function Dashboard() {
  const [isCreating, setIsCreating] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Получить все проекты
  const { data: projects, isLoading: projectsLoading } = useQuery(
    'projects',
    () => projectsApi.list().then(res => res.data)
  )

  // Получить видео для всех проектов
  const { data: allVideos } = useQuery(
    ['videos-all'],
    async () => {
      if (!projects) return {}
      const videosByProject: Record<number, Video[]> = {}

      await Promise.all(
        projects.map(async (project) => {
          const videos = await videosApi.listByProject(project.id).then(res => res.data)
          videosByProject[project.id] = videos
        })
      )

      return videosByProject
    },
    { enabled: !!projects }
  )

  // Создание проекта
  const createMutation = useMutation(
    (data: CreateProjectDto) => projectsApi.create(data),
    {
      onSuccess: async (newProject) => {
        queryClient.invalidateQueries('projects')
        setIsCreating(false)

        // Редирект на создание первого ролика
        navigate(`/project/${newProject.data.id}/create-video`)
      },
    }
  )

  if (projectsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Проекты</h1>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          <Plus className="h-5 w-5 mr-2" />
          Создать проект
        </button>
      </div>

      {/* Форма создания проекта */}
      {isCreating && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-semibold mb-4">Создать новый проект</h2>
          <ProjectForm
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setIsCreating(false)}
            isLoading={createMutation.isLoading}
          />
        </div>
      )}

      {/* Список проектов */}
      <div className="space-y-4">
        {projects?.map((project: Project) => (
          <ProjectCard
            key={project.id}
            project={project}
            videos={allVideos?.[project.id] || []}
            onCreateVideo={(projectId) => navigate(`/project/${projectId}/create-video`)}
            onEditProject={(projectId) => navigate(`/project/${projectId}/edit`)}
            onVideoClick={(videoId) => navigate(`/video/${videoId}`)}
          />
        ))}
      </div>

      {projects?.length === 0 && !isCreating && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">Нет проектов. Создайте первый!</p>
        </div>
      )}
    </div>
  )
}
