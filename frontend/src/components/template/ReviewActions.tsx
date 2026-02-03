import { useState } from 'react'
import { CheckCircle, XCircle, RefreshCw, Loader2 } from 'lucide-react'
import type { ScheduleSlot } from '@/services/api'

interface ReviewActionsProps {
  onApprove: () => void
  onReject: (reason: string, comment?: string) => void
  onRedo: (feedback?: string) => void
  targetSlot: ScheduleSlot | null
  disabled?: boolean
}

function formatSlotTime(scheduledAt: string): string {
  const date = new Date(scheduledAt)
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const day = days[date.getDay()]
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${day} ${hours}:${minutes}`
}

export function ReviewActions({ onApprove, onReject, onRedo, targetSlot, disabled }: ReviewActionsProps) {
  const [activeForm, setActiveForm] = useState<'reject' | 'redo' | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectComment, setRejectComment] = useState('')
  const [redoFeedback, setRedoFeedback] = useState('')

  const handleReject = () => {
    if (!rejectReason.trim()) return
    onReject(rejectReason.trim(), rejectComment.trim() || undefined)
    setActiveForm(null)
    setRejectReason('')
    setRejectComment('')
  }

  const handleRedo = () => {
    onRedo(redoFeedback.trim() || undefined)
    setActiveForm(null)
    setRedoFeedback('')
  }

  const toggleForm = (form: 'reject' | 'redo') => {
    setActiveForm(activeForm === form ? null : form)
  }

  const approveLabel = targetSlot
    ? `Approve → ${formatSlotTime(targetSlot.scheduled_at)}`
    : 'Approve → Queue'

  return (
    <div className="space-y-3">
      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => toggleForm('reject')}
          disabled={disabled}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition ${
            activeForm === 'reject'
              ? 'bg-red-100 text-red-700 border border-red-300'
              : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
          } disabled:opacity-50`}
        >
          <XCircle className="w-4 h-4" />
          Reject
        </button>
        <button
          onClick={() => toggleForm('redo')}
          disabled={disabled}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition ${
            activeForm === 'redo'
              ? 'bg-blue-100 text-blue-700 border border-blue-300'
              : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
          } disabled:opacity-50`}
        >
          <RefreshCw className="w-4 h-4" />
          Redo
        </button>
        <button
          onClick={onApprove}
          disabled={disabled}
          className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
        >
          {disabled ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <CheckCircle className="w-4 h-4" />
          )}
          {approveLabel}
        </button>
      </div>

      {/* Inline reject form */}
      {activeForm === 'reject' && (
        <div className="border border-red-200 rounded-lg p-4 space-y-3 bg-red-50">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., Poor video quality"
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Comment (optional)
            </label>
            <textarea
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="Additional details..."
              rows={2}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setActiveForm(null); setRejectReason(''); setRejectComment('') }}
              className="px-3 py-1.5 text-sm border rounded-lg hover:bg-white"
            >
              Cancel
            </button>
            <button
              onClick={handleReject}
              disabled={!rejectReason.trim()}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              Confirm Reject
            </button>
          </div>
        </div>
      )}

      {/* Inline redo form */}
      {activeForm === 'redo' && (
        <div className="border border-blue-200 rounded-lg p-4 space-y-3 bg-blue-50">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Feedback (optional)
            </label>
            <textarea
              value={redoFeedback}
              onChange={(e) => setRedoFeedback(e.target.value)}
              placeholder="What would you like to change? e.g., darker background, more dynamic pose..."
              rows={3}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
            />
            <p className="text-xs text-gray-500 mt-1">
              Leave empty to regenerate with original prompts
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setActiveForm(null); setRedoFeedback('') }}
              className="px-3 py-1.5 text-sm border rounded-lg hover:bg-white"
            >
              Cancel
            </button>
            <button
              onClick={handleRedo}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Regenerate
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
