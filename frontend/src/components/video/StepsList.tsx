import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import StatusIcon from './StatusIcon'
import StepContentRenderer from './StepContentRenderer'
import { getStepLabel } from '@/utils/video'
import type { WorkflowStep } from '@/types'

interface StepsListProps {
  steps: WorkflowStep[]
  completedCount: number
  totalSteps: number
  currentStepId?: number
  showProgress?: boolean
}

export default function StepsList({
  steps,
  completedCount,
  totalSteps,
  currentStepId,
  showProgress = false
}: StepsListProps) {
  const [showAllSteps, setShowAllSteps] = useState(false)
  const [expandedStepId, setExpandedStepId] = useState<number | null>(null)

  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <button
        onClick={() => setShowAllSteps(!showAllSteps)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
      >
        <div className="flex items-center space-x-3">
          <span className="font-medium text-gray-700">
            {showProgress ? `Completed steps (${completedCount})` : `All steps (${completedCount}/${totalSteps} completed)`}
          </span>
          {showProgress && (
            <div className="flex items-center space-x-1">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full ${
                    i < completedCount ? 'bg-green-500' :
                    i === completedCount ? 'bg-purple-500' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          )}
        </div>
        {showAllSteps ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
      </button>

      {showAllSteps && (
        <div className="border-t">
          {steps.map((step, index) => (
            <div key={step.id} className="border-b last:border-0">
              <button
                onClick={() => setExpandedStepId(expandedStepId === step.id ? null : step.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 transition ${
                  step.id === currentStepId ? 'bg-purple-50' : ''
                } ${expandedStepId === step.id ? 'bg-gray-50' : ''}`}
              >
                <StatusIcon status={step.status} />
                <span className="text-sm text-gray-500 w-16">Step {index + 1}</span>
                <span className={`text-sm font-medium ${
                  step.id === currentStepId ? 'text-purple-700' : 'text-gray-700'
                }`}>
                  {getStepLabel(step.step_type)}
                </span>
                <span className="text-xs text-gray-400 capitalize ml-auto mr-2">
                  {step.status?.toLowerCase().replace('_', ' ')}
                </span>
                {step.content && (
                  expandedStepId === step.id
                    ? <ChevronDown className="h-4 w-4 text-gray-400" />
                    : <ChevronRight className="h-4 w-4 text-gray-400" />
                )}
              </button>
              {expandedStepId === step.id && step.content && (
                <div className="px-4 pb-4 pt-2 bg-gray-50 border-t">
                  <div className="text-sm text-gray-700">
                    <StepContentRenderer stepType={step.step_type} content={step.content} />
                  </div>
                  {step.generation_time_seconds && (
                    <div className="mt-2 text-xs text-gray-400">
                      Generated in {step.generation_time_seconds.toFixed(1)}s
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
