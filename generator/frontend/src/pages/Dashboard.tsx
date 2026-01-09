import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, FolderOpen, Settings, Film, AlertCircle, CheckCircle, Clock, Image, Eye, Heart, MessageCircle, Share2 } from 'lucide-react'
import { projectsApi, videosApi, workspacesApi } from '@/services/api'
import ProjectForm from '@/components/ProjectForm'
import type { Project, Video, CreateProjectDto, StepType, Workspace } from '@/types'

type FilterTab = 'all' | 'in_progress' | 'published' | 'errors'

const STEP_ORDER: StepType[] = ['story', 'description', 'prompt', 'image', 'scenario', 'video', 'audio', 'adaptation', 'publishing']

function getStepIndex(step: StepType): number {
  return STEP_ORDER.indexOf(step)
}

function getStepLabel(step: StepType): string {
  const map: Record<StepType, string> = {
    story: 'Story',
    description: 'Description',
    prompt: 'Prompt',
    image: 'Image',
    scenario: 'Scenario',
    video: 'Video',
    audio: 'Audio',
    adaptation: 'Adaptation',
    publishing: 'Publishing'
  }
  return map[step] || step
}

export default function Dashboard() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Получить все проекты
  const { data: projects, isLoading: projectsLoading } = useQuery(
    'projects',
    () => projectsApi.list().then(res => res.data)
  )

  // Получить workspaces пользователя
  const { data: workspaces } = useQuery<Workspace[]>(
    'workspaces',
    () => workspacesApi.list().then(res => res.data)
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
        setIsCreatingProject(false)
        setSelectedProjectId(newProject.data.id)
      },
    }
  )

  // Собрать все видео в один массив с фильтрацией
  const filteredVideos = useMemo(() => {
    if (!allVideos) return []

    let videos: Video[] = []

    // Фильтр по проекту
    if (selectedProjectId) {
      videos = allVideos[selectedProjectId] || []
    } else {
      // Все видео из всех проектов
      Object.values(allVideos).forEach(projectVideos => {
        videos = [...videos, ...projectVideos]
      })
    }

    // Фильтр по статусу (case-insensitive)
    switch (activeFilter) {
      case 'in_progress':
        return videos.filter(v => {
          const s = v.status?.toLowerCase() || ''
          return s === 'pending' || s === 'in_progress' || s === 'awaiting_approval' || s === 'validating'
        })
      case 'published':
        return videos.filter(v => v.status?.toLowerCase() === 'completed')
      case 'errors':
        return videos.filter(v => {
          const s = v.status?.toLowerCase() || ''
          return s === 'failed' || s === 'validation_failed'
        })
      default:
        return videos
    }
  }, [allVideos, selectedProjectId, activeFilter])

  // Подсчёт для бейджей
  const counts = useMemo(() => {
    if (!allVideos) return { all: 0, in_progress: 0, published: 0, errors: 0 }

    let videos: Video[] = []
    if (selectedProjectId) {
      videos = allVideos[selectedProjectId] || []
    } else {
      Object.values(allVideos).forEach(projectVideos => {
        videos = [...videos, ...projectVideos]
      })
    }

    return {
      all: videos.length,
      in_progress: videos.filter(v => {
        const s = v.status?.toLowerCase() || ''
        return s === 'pending' || s === 'in_progress' || s === 'awaiting_approval' || s === 'validating'
      }).length,
      published: videos.filter(v => v.status?.toLowerCase() === 'completed').length,
      errors: videos.filter(v => {
        const s = v.status?.toLowerCase() || ''
        return s === 'failed' || s === 'validation_failed'
      }).length
    }
  }, [allVideos, selectedProjectId])

  if (projectsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const tabs: { key: FilterTab; label: string; count: number }[] = [
    { key: 'all', label: 'Все', count: counts.all },
    { key: 'in_progress', label: 'В работе', count: counts.in_progress },
    { key: 'published', label: 'Опубликовано', count: counts.published },
    { key: 'errors', label: 'Ошибки', count: counts.errors },
  ]

  return (
    <div className="flex h-[calc(100vh-80px)]">
      {/* Sidebar - Список проектов */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Проекты</h2>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* "Все проекты" option */}
          <button
            onClick={() => setSelectedProjectId(null)}
            className={`w-full flex items-center px-4 py-3 text-left hover:bg-gray-50 transition ${
              selectedProjectId === null ? 'bg-purple-50 border-r-2 border-purple-600' : ''
            }`}
          >
            <FolderOpen className={`h-5 w-5 mr-3 ${selectedProjectId === null ? 'text-purple-600' : 'text-gray-400'}`} />
            <span className={selectedProjectId === null ? 'text-purple-600 font-medium' : 'text-gray-700'}>
              Все проекты
            </span>
          </button>

          {/* Список проектов */}
          {projects?.map((project: Project) => {
            const projectVideoCount = allVideos?.[project.id]?.length || 0
            return (
              <button
                key={project.id}
                onClick={() => setSelectedProjectId(project.id)}
                className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition ${
                  selectedProjectId === project.id ? 'bg-purple-50 border-r-2 border-purple-600' : ''
                }`}
              >
                <div className="flex items-center flex-1 min-w-0">
                  <FolderOpen className={`h-5 w-5 mr-3 flex-shrink-0 ${
                    selectedProjectId === project.id ? 'text-purple-600' : 'text-gray-400'
                  }`} />
                  <span className={`truncate ${
                    selectedProjectId === project.id ? 'text-purple-600 font-medium' : 'text-gray-700'
                  }`}>
                    {project.name}
                  </span>
                </div>
                <span className="text-xs text-gray-400 ml-2">{projectVideoCount}</span>
              </button>
            )
          })}
        </div>

        {/* Кнопка создания проекта */}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={() => setIsCreatingProject(true)}
            className="w-full flex items-center justify-center px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
          >
            <Plus className="h-4 w-4 mr-2" />
            Новый проект
          </button>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header с табами */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">
              {selectedProjectId
                ? projects?.find(p => p.id === selectedProjectId)?.name || 'Проект'
                : 'Все видео'
              }
            </h1>
            {selectedProjectId && (
              <button
                onClick={() => navigate(`/project/${selectedProjectId}/edit`)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <Settings className="h-5 w-5" />
              </button>
            )}
          </div>

          {/* Filter tabs */}
          <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
            {tabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveFilter(tab.key)}
                className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition ${
                  activeFilter === tab.key
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                    activeFilter === tab.key
                      ? 'bg-purple-100 text-purple-600'
                      : 'bg-gray-200 text-gray-500'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Video grid */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {/* "+ New Video" card - всегда первый */}
            {selectedProjectId && (
              <button
                onClick={() => navigate(`/project/${selectedProjectId}/create-video`)}
                className="aspect-video bg-gray-50 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center hover:border-purple-400 hover:bg-purple-50 transition group"
              >
                <div className="w-12 h-12 rounded-full bg-gray-200 group-hover:bg-purple-100 flex items-center justify-center mb-3 transition">
                  <Plus className="h-6 w-6 text-gray-400 group-hover:text-purple-600 transition" />
                </div>
                <span className="text-gray-500 group-hover:text-purple-600 font-medium transition">
                  Новый ролик
                </span>
              </button>
            )}

            {/* Video cards */}
            {filteredVideos.map(video => (
              <VideoGridCard
                key={video.id}
                video={video}
                onClick={() => navigate(`/video/${video.id}`)}
                showProjectName={!selectedProjectId}
                projectName={projects?.find(p => p.id === video.project_id)?.name}
              />
            ))}
          </div>

          {/* Empty state */}
          {filteredVideos.length === 0 && !selectedProjectId && (
            <div className="text-center py-16">
              <Film className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Нет видео</h3>
              <p className="text-gray-500 mb-6">
                {activeFilter === 'all'
                  ? 'Выберите проект и создайте первый ролик'
                  : `Нет видео в категории "${tabs.find(t => t.key === activeFilter)?.label}"`
                }
              </p>
            </div>
          )}

          {filteredVideos.length === 0 && selectedProjectId && (
            <div className="col-span-full text-center py-8">
              <p className="text-gray-500">
                {activeFilter === 'all'
                  ? 'Создайте первый ролик в этом проекте'
                  : `Нет видео в категории "${tabs.find(t => t.key === activeFilter)?.label}"`
                }
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create project */}
      {isCreatingProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-semibold p-6 pb-4 border-b">Создать проект</h2>
            <div className="overflow-y-auto p-6 pt-4">
              <ProjectForm
                workspaces={workspaces}
                onSubmit={(data) => createMutation.mutate(data)}
                onCancel={() => setIsCreatingProject(false)}
                isLoading={createMutation.isLoading}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Компонент карточки видео для grid
interface VideoGridCardProps {
  video: Video
  onClick: () => void
  showProjectName?: boolean
  projectName?: string
}

// Platform icons
const InstagramIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
  </svg>
)

const TikTokIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
)

const YouTubeIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
)

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short'
  })
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

function getLatestMetrics(video: Video) {
  if (!video.metrics || video.metrics.length === 0) return null

  // Aggregate metrics across platforms, prefer latest period
  const periodPriority = ['7d', '24h', '6h', '30m']
  let totalViews = 0
  let totalLikes = 0
  let totalComments = 0
  let totalShares = 0

  // Group by platform, take best period for each
  const platforms = new Set(video.metrics.map(m => m.platform))

  for (const platform of platforms) {
    const platformMetrics = video.metrics.filter(m => m.platform === platform)
    // Find the latest period available
    for (const period of periodPriority) {
      const metric = platformMetrics.find(m => m.period === period)
      if (metric) {
        totalViews += metric.views
        totalLikes += metric.likes
        totalComments += metric.comments
        totalShares += metric.shares
        break
      }
    }
  }

  if (totalViews === 0 && totalLikes === 0) return null

  return { views: totalViews, likes: totalLikes, comments: totalComments, shares: totalShares }
}

function VideoGridCard({ video, onClick, showProjectName, projectName }: VideoGridCardProps) {
  const stepIndex = getStepIndex(video.current_step)
  const statusLower = video.status?.toLowerCase() || ''
  const isInProgress = ['pending', 'in_progress', 'awaiting_approval', 'validating'].includes(statusLower)
  const isPublished = statusLower === 'completed'
  const isError = statusLower === 'failed' || statusLower === 'validation_failed'
  const metrics = getLatestMetrics(video)

  // Progress indicator dots
  const progressDots = STEP_ORDER.map((_, i) => (
    <span
      key={i}
      className={`w-2 h-2 rounded-full ${
        i < stepIndex ? 'bg-purple-600' :
        i === stepIndex ? 'bg-purple-400' :
        'bg-gray-300'
      }`}
    />
  ))

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl shadow-sm hover:shadow-md transition cursor-pointer overflow-hidden border border-gray-100"
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-gray-100 relative">
        {video.image_url ? (
          <img
            src={video.image_url}
            alt={video.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Image className="h-12 w-12 text-gray-300" />
          </div>
        )}

        {/* Status badge */}
        <div className="absolute top-2 right-2">
          {isPublished && (
            <span className="px-2 py-1 bg-green-500 text-white text-xs font-medium rounded-full flex items-center">
              <CheckCircle className="h-3 w-3 mr-1" />
              Published
            </span>
          )}
          {isError && (
            <span className="px-2 py-1 bg-red-500 text-white text-xs font-medium rounded-full flex items-center">
              <AlertCircle className="h-3 w-3 mr-1" />
              Error
            </span>
          )}
          {isInProgress && (
            <span className="px-2 py-1 bg-yellow-500 text-white text-xs font-medium rounded-full flex items-center">
              <Clock className="h-3 w-3 mr-1" />
              {getStepLabel(video.current_step)}
            </span>
          )}
        </div>

        {/* Workflow mode badge */}
        {video.workflow_mode === 'MANUAL' && (
          <div className="absolute top-2 left-2">
            <span className="px-2 py-1 bg-blue-500 text-white text-xs font-medium rounded-full">
              Manual
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-medium text-gray-900 truncate mb-1">{video.title}</h3>

        {showProjectName && projectName && (
          <p className="text-xs text-gray-500 mb-2">{projectName}</p>
        )}

        {/* Progress indicator for in-progress videos */}
        {isInProgress && (
          <div className="flex items-center gap-1 mb-2">
            {progressDots}
          </div>
        )}

        {/* Key dates */}
        <div className="text-xs text-gray-400 space-y-0.5">
          <p>Created: {formatDate(video.created_at)}</p>
          {video.updated_at !== video.created_at && (
            <p>Updated: {formatDate(video.updated_at)}</p>
          )}
          {isPublished && (
            <p className="text-green-600">Published: {formatDate(video.updated_at)}</p>
          )}
        </div>

        {/* Platform icons (if completed) */}
        {isPublished && video.project?.platforms && (
          <div className="flex items-center gap-2 mt-2">
            {video.project.platforms.includes('instagram') && (
              <InstagramIcon className="w-4 h-4 text-pink-500" />
            )}
            {video.project.platforms.includes('tiktok') && (
              <TikTokIcon className="w-4 h-4 text-gray-900" />
            )}
            {video.project.platforms.includes('youtube') && (
              <YouTubeIcon className="w-4 h-4 text-red-500" />
            )}
          </div>
        )}

        {/* Metrics (if published and has data) */}
        {isPublished && metrics && (
          <div className="flex items-center gap-3 mt-2 pt-2 border-t border-gray-100 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Eye className="w-3 h-3" />
              {formatNumber(metrics.views)}
            </span>
            <span className="flex items-center gap-1">
              <Heart className="w-3 h-3" />
              {formatNumber(metrics.likes)}
            </span>
            <span className="flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />
              {formatNumber(metrics.comments)}
            </span>
            {metrics.shares > 0 && (
              <span className="flex items-center gap-1">
                <Share2 className="w-3 h-3" />
                {formatNumber(metrics.shares)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
