import { Video } from '@/types'
import { Clock, CheckCircle, XCircle, Film } from 'lucide-react'
import { formatDate } from '@/utils/date'

interface VideoCardProps {
  video: Video
  onClick: () => void
}

export default function VideoCard({ video, onClick }: VideoCardProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />
    }
  }

  const getStepLabel = (step: string) => {
    const map: Record<string, string> = {
      story: 'Story',
      description: 'Description',
      prompt: 'Prompt',
      image: 'Image',
      scenario: 'Scenario',
      video: 'Video',
      adaptation: 'Adaptation',
      publishing: 'Publishing'
    }
    return map[step] || step
  }

  return (
    <div
      onClick={onClick}
      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition"
    >
      <div className="flex items-center space-x-3 flex-1">
        <Film className="h-5 w-5 text-primary-600" />

        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium text-gray-900">{video.title}</h4>
            {video.workflow_mode === 'MANUAL' && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                Manual
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500">
            <span>Step: {getStepLabel(video.current_step)}</span>
            <span>•</span>
            <span>{formatDate(video.created_at, 'date')}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {getStatusIcon(video.status)}
        <span className="text-sm text-gray-600 capitalize">
          {video.status.replace('_', ' ')}
        </span>
      </div>
    </div>
  )
}
