import { FolderOpen, Plus, Compass, Repeat, LayoutTemplate } from 'lucide-react'
import type { Project, Video } from '@/types'

interface ProjectSidebarProps {
  projects: Project[] | undefined
  allVideos: Record<number, Video[]> | undefined
  templateGenerationCounts?: Record<number, number>
  selectedProjectId: number | null
  onSelectProject: (id: number | null) => void
  onCreateProject: () => void
}

export default function ProjectSidebar({
  projects,
  allVideos,
  templateGenerationCounts,
  selectedProjectId,
  onSelectProject,
  onCreateProject
}: ProjectSidebarProps) {
  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Проекты</h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* "All projects" option */}
        <button
          onClick={() => onSelectProject(null)}
          className={`w-full flex items-center px-4 py-3 text-left hover:bg-gray-50 transition ${
            selectedProjectId === null ? 'bg-purple-50 border-r-2 border-purple-600' : ''
          }`}
        >
          <FolderOpen className={`h-5 w-5 mr-3 ${selectedProjectId === null ? 'text-purple-600' : 'text-gray-400'}`} />
          <span className={selectedProjectId === null ? 'text-purple-600 font-medium' : 'text-gray-700'}>
            Все проекты
          </span>
        </button>

        {/* Project list */}
        {projects?.map((project: Project) => {
          // Use generation count for template projects, video count for others
          const videoCount = project.project_type === 'template'
            ? templateGenerationCounts?.[project.id] || 0
            : allVideos?.[project.id]?.length || 0
          const isSelected = selectedProjectId === project.id

          return (
            <button
              key={project.id}
              onClick={() => onSelectProject(project.id)}
              className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition ${
                isSelected ? 'bg-purple-50 border-r-2 border-purple-600' : ''
              }`}
            >
              <div className="flex items-center flex-1 min-w-0">
                {project.project_type === 'remix' ? (
                  <Repeat className={`h-5 w-5 mr-3 flex-shrink-0 ${isSelected ? 'text-purple-600' : 'text-purple-400'}`} />
                ) : project.project_type === 'template' ? (
                  <LayoutTemplate className={`h-5 w-5 mr-3 flex-shrink-0 ${isSelected ? 'text-purple-600' : 'text-green-500'}`} />
                ) : (
                  <Compass className={`h-5 w-5 mr-3 flex-shrink-0 ${isSelected ? 'text-purple-600' : 'text-blue-400'}`} />
                )}
                <span className={`truncate ${isSelected ? 'text-purple-600 font-medium' : 'text-gray-700'}`}>
                  {project.name}
                </span>
              </div>
              <span className="text-xs text-gray-400 ml-2">{videoCount}</span>
            </button>
          )
        })}
      </div>

      {/* Create project button */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={onCreateProject}
          className="w-full flex items-center justify-center px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
        >
          <Plus className="h-4 w-4 mr-2" />
          Новый проект
        </button>
      </div>
    </div>
  )
}
