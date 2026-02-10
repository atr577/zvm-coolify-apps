import { ArrowLeft, Settings, Trash2, CheckCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface VideoHeaderProps {
  title: string
  completedCount: number
  totalSteps: number
  isCompleted: boolean
  workflowMode: string
  isRemix: boolean
  projectId?: number
  onToggleMode: () => void
  onDelete: () => void
}

export default function VideoHeader({
  title,
  completedCount,
  totalSteps,
  isCompleted,
  workflowMode,
  isRemix,
  projectId,
  onToggleMode,
  onDelete,
}: VideoHeaderProps) {
  const navigate = useNavigate()

  const handleBack = () => {
    // Navigate back to project if we came from one
    if (projectId) {
      navigate(`/dashboard?project=${projectId}`)
    } else {
      navigate('/dashboard')
    }
  }

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={handleBack}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900 line-clamp-1">{title}</h1>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            {isCompleted ? (
              <span className="flex items-center text-green-600">
                <CheckCircle className="h-4 w-4 mr-1" />
                Completed
              </span>
            ) : (
              <span>Step {completedCount + 1} of {totalSteps}</span>
            )}
            {workflowMode === 'MANUAL' && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">Manual</span>
            )}
            {isRemix && (
              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">Remix</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <button
          onClick={onToggleMode}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
          title={workflowMode === 'MANUAL' ? 'Switch to Auto mode' : 'Switch to Manual mode'}
        >
          <Settings className="h-5 w-5 text-gray-500" />
        </button>
        <button
          onClick={onDelete}
          className="p-2 hover:bg-red-50 rounded-lg transition"
        >
          <Trash2 className="h-5 w-5 text-red-500" />
        </button>
      </div>
    </div>
  )
}
