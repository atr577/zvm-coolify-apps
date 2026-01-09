import { useState } from 'react'
import { ChevronDown, ChevronRight, Settings, Plus } from 'lucide-react'
import { Project, Video } from '@/types'
import VideoCard from './VideoCard'

interface ProjectCardProps {
  project: Project
  videos: Video[]
  onCreateVideo: (projectId: number) => void
  onEditProject: (projectId: number) => void
  onVideoClick: (videoId: number) => void
}

export default function ProjectCard({
  project,
  videos,
  onCreateVideo,
  onEditProject,
  onVideoClick
}: ProjectCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const publishedCount = videos.filter(v => v.status === 'completed').length
  const latestVideos = videos.slice(0, 3)

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition">
      {/* Header - клик раскрывает */}
      <div
        className="p-6 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <button className="mt-1">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronRight className="h-5 w-5 text-gray-500" />
              )}
            </button>

            <div className="flex-1">
              <h3 className="text-xl font-semibold text-gray-900 mb-1">
                📁 {project.name}
              </h3>
              {project.description && (
                <p className="text-sm text-gray-600 mb-2">{project.description}</p>
              )}

              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>{videos.length} роликов</span>
                <span>•</span>
                <span>{publishedCount} опубликовано</span>
              </div>
            </div>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation()
              onEditProject(project.id)
            }}
            className="text-gray-400 hover:text-primary-600 transition"
          >
            <Settings className="h-5 w-5" />
          </button>
        </div>

        {/* Preview последних роликов (если не раскрыто) */}
        {!isExpanded && videos.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-gray-500 uppercase">Последние:</p>
            {latestVideos.map(video => (
              <div key={video.id} className="text-sm text-gray-700">
                • {video.title} - {getStatusLabel(video.status)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Expanded content - список всех роликов */}
      {isExpanded && (
        <div className="px-6 pb-6 border-t">
          <div className="mt-4 space-y-3">
            {videos.map(video => (
              <VideoCard
                key={video.id}
                video={video}
                onClick={() => onVideoClick(video.id)}
              />
            ))}

            {videos.length === 0 && (
              <p className="text-center text-gray-500 py-8">
                Нет роликов в этом проекте
              </p>
            )}
          </div>

          <button
            onClick={() => onCreateVideo(project.id)}
            className="mt-4 w-full flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
          >
            <Plus className="h-5 w-5 mr-2" />
            Создать новый ролик
          </button>
        </div>
      )}
    </div>
  )
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '📝 Черновик',
    in_progress: '🔄 Генерация',
    completed: '✅ Опубликован',
    failed: '❌ Ошибка'
  }
  return map[status] || status
}
