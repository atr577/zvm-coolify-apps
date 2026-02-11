import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from 'react-query'
import { Plus, Film, Settings } from 'lucide-react'
import { useDashboardData, FilterTab } from '@/hooks/useDashboardData'
import ProjectForm from '@/components/ProjectForm'
import { TemplateProjectForm, TemplateProjectView, type TemplateProjectCreateDto } from '@/components/template'
import { DiscoverProjectForm, type DiscoverProjectFormData } from '@/components/discover'
import { templateApi, discoverApi } from '@/services/api'
import ProjectSidebar from '@/components/dashboard/ProjectSidebar'
import VideoGridCard from '@/components/dashboard/VideoGridCard'
import DashboardAnalytics from '@/components/dashboard/DashboardAnalytics'

type ProjectTypeSelection = 'discover' | 'remix' | 'template' | null

export default function Dashboard() {
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [selectedProjectType, setSelectedProjectType] = useState<ProjectTypeSelection>(null)
  const [isCreatingTemplate, setIsCreatingTemplate] = useState(false)
  const [isCreatingDiscover, setIsCreatingDiscover] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    selectedProjectId,
    activeFilter,
    setSelectedProjectId,
    setActiveFilter,
    projects,
    discoverProjects,
    workspaces,
    allVideos,
    templateGenerationCounts,
    filteredVideos,
    counts,
    projectsLoading,
    createProject,
    isCreating,
  } = useDashboardData()

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
    { key: 'ready', label: 'Готово', count: counts.ready },
    { key: 'published', label: 'Опубликовано', count: counts.published },
    { key: 'errors', label: 'Ошибки', count: counts.errors },
  ]

  const selectedProject = projects?.find(p => p.id === selectedProjectId)

  return (
    <div className="flex h-[calc(100vh-80px)]">
      {/* Sidebar */}
      <ProjectSidebar
        projects={projects}
        discoverProjects={discoverProjects}
        allVideos={allVideos}
        templateGenerationCounts={templateGenerationCounts}
        selectedProjectId={selectedProjectId}
        onSelectProject={setSelectedProjectId}
        onCreateProject={() => setIsCreatingProject(true)}
      />

      {/* Main content */}
      {/* Template project view */}
      {selectedProject?.project_type === 'template' ? (
        <TemplateProjectView
          projectId={selectedProjectId!}
          projectName={selectedProject.name}
        />
      ) : selectedProjectId === null ? (
        <DashboardAnalytics onSelectProject={setSelectedProjectId} />
      ) : (
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header with tabs */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">
              {selectedProjectId ? selectedProject?.name || 'Проект' : 'Все видео'}
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
            {/* "+ New Video" card */}
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

          {/* Empty states */}
          {filteredVideos.length === 0 && (
            <EmptyState
              hasProject={!!selectedProjectId}
              activeFilter={activeFilter}
              tabs={tabs}
            />
          )}
        </div>
      </div>
      )}

      {/* Modal: Create project - Step 1: Select type */}
      {isCreatingProject && !selectedProjectType && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <h2 className="text-xl font-semibold p-6 pb-4 border-b">Выберите тип проекта</h2>
            <div className="p-6 space-y-3">
              {[
                { value: 'discover' as const, label: 'Discover', description: 'Полный воркфлоу: Story → Image → Video' },
                { value: 'remix' as const, label: 'Remix', description: 'Быстрая генерация по шаблону' },
                { value: 'template' as const, label: 'Template', description: 'CSV варианты → многошаговая генерация' },
              ].map(type => (
                <button
                  key={type.value}
                  onClick={() => setSelectedProjectType(type.value)}
                  className="w-full p-4 text-left border-2 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition"
                >
                  <span className="font-medium text-gray-900">{type.label}</span>
                  <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                </button>
              ))}
            </div>
            <div className="p-6 pt-0">
              <button
                onClick={() => setIsCreatingProject(false)}
                className="w-full py-2 text-gray-600 hover:text-gray-900"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create project - Step 2: Discover form */}
      {isCreatingProject && selectedProjectType === 'discover' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-semibold p-6 pb-4 border-b">Create Discover Project</h2>
            <div className="overflow-y-auto p-6 pt-4">
              <DiscoverProjectForm
                workspaces={workspaces}
                onSubmit={async (data: DiscoverProjectFormData) => {
                  setIsCreatingDiscover(true)
                  try {
                    const res = await discoverApi.create(data)
                    setIsCreatingProject(false)
                    setSelectedProjectType(null)
                    navigate(`/discover/${res.data.id}`)
                  } catch (err) {
                    console.error('Failed to create discover project:', err)
                    alert('Failed to create project')
                  } finally {
                    setIsCreatingDiscover(false)
                  }
                }}
                onCancel={() => {
                  setIsCreatingProject(false)
                  setSelectedProjectType(null)
                }}
                isLoading={isCreatingDiscover}
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create project - Step 2: Remix form */}
      {isCreatingProject && selectedProjectType === 'remix' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-semibold p-6 pb-4 border-b">
              Создать проект (Remix)
            </h2>
            <div className="overflow-y-auto p-6 pt-4">
              <ProjectForm
                initialData={{ project_type: 'remix' }}
                workspaces={workspaces}
                onSubmit={(data) => {
                  createProject({ ...data, project_type: 'remix' })
                  setIsCreatingProject(false)
                  setSelectedProjectType(null)
                }}
                onCancel={() => {
                  setIsCreatingProject(false)
                  setSelectedProjectType(null)
                }}
                isLoading={isCreating}
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create project - Step 2: Template form */}
      {isCreatingProject && selectedProjectType === 'template' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-semibold p-6 pb-4 border-b">Создать Template проект</h2>
            <div className="overflow-y-auto p-6 pt-4">
              <TemplateProjectForm
                workspaces={workspaces}
                onSubmit={async (data: TemplateProjectCreateDto) => {
                  setIsCreatingTemplate(true)
                  try {
                    const res = await templateApi.createProject(data)
                    queryClient.invalidateQueries('projects')
                    setIsCreatingProject(false)
                    setSelectedProjectType(null)
                    setSelectedProjectId(res.data.id)
                  } catch (err) {
                    console.error('Failed to create template project:', err)
                    alert('Failed to create project')
                  } finally {
                    setIsCreatingTemplate(false)
                  }
                }}
                onCancel={() => {
                  setIsCreatingProject(false)
                  setSelectedProjectType(null)
                }}
                isLoading={isCreatingTemplate}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface EmptyStateProps {
  hasProject: boolean
  activeFilter: FilterTab
  tabs: { key: FilterTab; label: string }[]
}

function EmptyState({ hasProject, activeFilter, tabs }: EmptyStateProps) {
  const filterLabel = tabs.find(t => t.key === activeFilter)?.label

  if (!hasProject) {
    return (
      <div className="text-center py-16">
        <Film className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Нет видео</h3>
        <p className="text-gray-500 mb-6">
          {activeFilter === 'all'
            ? 'Выберите проект и создайте первый ролик'
            : `Нет видео в категории "${filterLabel}"`}
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-full text-center py-8">
      <p className="text-gray-500">
        {activeFilter === 'all'
          ? 'Создайте первый ролик в этом проекте'
          : `Нет видео в категории "${filterLabel}"`}
      </p>
    </div>
  )
}
