import { useRef, useEffect } from 'react'
import { ChevronDown, ChevronUp, CheckCircle, Clock, Loader2, AlertTriangle, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react'
import type { WorkflowStep } from '@/types'

interface StepCardProps {
  stepNumber: number
  title: string
  icon: React.ReactNode
  status: 'pending' | 'loading' | 'review' | 'approved' | 'rejected'
  isExpanded: boolean
  onToggle: () => void
  children?: React.ReactNode
  workflowStep?: WorkflowStep
  onApprove?: (stepId: number) => void
  onReject?: (stepId: number) => void
  onRestart?: (stepId: number) => void
  feedback?: string
  onFeedbackChange?: (feedback: string) => void
  loadingMessage?: string
}

export default function StepCard({
  stepNumber,
  title,
  icon,
  status,
  isExpanded,
  onToggle,
  children,
  workflowStep,
  onApprove,
  onReject,
  onRestart,
  feedback,
  onFeedbackChange,
  loadingMessage
}: StepCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Auto-scroll to this card when it becomes active (loading or review)
    if ((status === 'loading' || status === 'review') && isExpanded) {
      setTimeout(() => {
        cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 300)
    }
  }, [status, isExpanded])

  const getStatusIcon = () => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'loading':
        return <Loader2 className="h-5 w-5 text-primary-600 animate-spin" />
      case 'review':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />
      case 'rejected':
        return <AlertTriangle className="h-5 w-5 text-red-500" />
      case 'pending':
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'approved':
        return <span className="text-green-600 font-medium">Approved</span>
      case 'loading':
        return <span className="text-primary-600 font-medium animate-pulse">Generating...</span>
      case 'review':
        return <span className="text-yellow-600 font-medium">Awaiting Review</span>
      case 'rejected':
        return <span className="text-red-600 font-medium">Rejected</span>
      case 'pending':
        return <span className="text-gray-500">Waiting</span>
    }
  }

  const getCardStyle = () => {
    switch (status) {
      case 'approved':
        return 'bg-green-50 border-green-200'
      case 'loading':
        return 'bg-primary-50 border-primary-300 shadow-lg ring-2 ring-primary-200'
      case 'review':
        return 'bg-yellow-50 border-yellow-300 shadow-lg ring-2 ring-yellow-200'
      case 'rejected':
        return 'bg-red-50 border-red-200'
      case 'pending':
        return 'bg-gray-50 border-gray-200'
    }
  }

  const latestValidation = workflowStep?.validations[workflowStep.validations.length - 1]

  return (
    <div ref={cardRef} className={`rounded-lg border-2 transition-all duration-300 ${getCardStyle()}`}>
      {/* Header - always visible */}
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-black hover:bg-opacity-5 transition-colors"
      >
        <div className="flex items-center space-x-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-white shadow-sm">
            {icon}
          </div>
          <div className="text-left">
            <h3 className="text-lg font-semibold text-gray-900">
              Step {stepNumber}: {title}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              {getStatusIcon()}
              {getStatusText()}
            </div>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-gray-500" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-500" />
        )}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-6 pb-6 border-t border-gray-200">
          {/* Loading state */}
          {status === 'loading' && (
            <div className="py-8 text-center">
              <Loader2 className="h-12 w-12 text-primary-600 animate-spin mx-auto mb-4" />
              <p className="text-lg font-medium text-gray-900 mb-2">
                {loadingMessage || 'Generating content...'}
              </p>
              <p className="text-sm text-gray-500 mb-4">Please wait, this usually takes 5-15 seconds</p>
              {workflowStep && onRestart && (
                <button
                  onClick={() => onRestart(workflowStep.id)}
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition"
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Restart Step
                </button>
              )}
            </div>
          )}

          {/* Review state - show content and approve/reject buttons */}
          {status === 'review' && workflowStep && (
            <div className="py-4">
              {/* Validation badge */}
              {latestValidation && (
                <div className="mb-4">
                  {latestValidation.status === 'pass' && (
                    <div className="flex items-center text-green-600 bg-green-100 px-3 py-2 rounded-md">
                      <CheckCircle className="h-5 w-5 mr-2" />
                      <span className="font-medium">Validation Passed ({latestValidation.score}/100)</span>
                    </div>
                  )}
                  {latestValidation.status === 'pass_with_warnings' && (
                    <div className="flex items-center text-yellow-600 bg-yellow-100 px-3 py-2 rounded-md">
                      <AlertTriangle className="h-5 w-5 mr-2" />
                      <span className="font-medium">Passed with Warnings ({latestValidation.score}/100)</span>
                    </div>
                  )}
                </div>
              )}

              {/* Content */}
              <div className="bg-white rounded-lg p-4 mb-4 max-h-[600px] overflow-auto">
                {children}
              </div>

              {/* Validation warnings/recommendations */}
              {latestValidation?.warnings && latestValidation.warnings.length > 0 && (
                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
                  <h4 className="text-sm font-medium text-yellow-800 mb-2">⚠️ Warnings</h4>
                  <ul className="text-sm text-yellow-700 list-disc list-inside space-y-1">
                    {latestValidation.warnings.map((warning, i) => (
                      <li key={i}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {latestValidation?.recommendations && latestValidation.recommendations.length > 0 && (
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
                  <h4 className="text-sm font-medium text-blue-800 mb-2">💡 Recommendations</h4>
                  <ul className="text-sm text-blue-700 list-disc list-inside space-y-1">
                    {latestValidation.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Feedback textarea */}
              <textarea
                value={feedback}
                onChange={(e) => onFeedbackChange?.(e.target.value)}
                placeholder="Optional feedback for regeneration..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md mb-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={2}
              />

              {/* Approve/Reject buttons */}
              <div className="flex space-x-3">
                <button
                  onClick={() => onApprove?.(workflowStep.id)}
                  className="flex-1 flex items-center justify-center px-4 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition font-medium"
                >
                  <ThumbsUp className="h-5 w-5 mr-2" />
                  Approve & Continue
                </button>
                <button
                  onClick={() => onReject?.(workflowStep.id)}
                  className="flex-1 flex items-center justify-center px-4 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 transition font-medium"
                >
                  <ThumbsDown className="h-5 w-5 mr-2" />
                  Reject & Regenerate
                </button>
              </div>
            </div>
          )}

          {/* Approved state - show collapsed summary */}
          {status === 'approved' && (
            <div className="py-4">
              <div className="bg-green-100 border border-green-200 rounded-md p-4 mb-4">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                  <span className="text-sm font-medium text-green-800">
                    Step approved and completed
                  </span>
                </div>
              </div>
              {/* Show content if expanded */}
              <div className="bg-white rounded-lg p-4 max-h-[600px] overflow-auto">
                {children}
              </div>
            </div>
          )}

          {/* Pending state */}
          {status === 'pending' && (
            <div className="py-4">
              {children ? (
                // If children provided, show them (e.g., input form)
                children
              ) : (
                // Otherwise show waiting message
                <div className="py-8 text-center">
                  <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">Waiting for previous steps to complete...</p>
                </div>
              )}
            </div>
          )}

          {/* Rejected state */}
          {status === 'rejected' && (
            <div className="py-4">
              <div className="bg-red-100 border border-red-200 rounded-md p-4 mb-4">
                <div className="flex items-center">
                  <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
                  <span className="text-sm font-medium text-red-800">
                    Step rejected - ready for regeneration
                  </span>
                </div>
              </div>
              {children}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
