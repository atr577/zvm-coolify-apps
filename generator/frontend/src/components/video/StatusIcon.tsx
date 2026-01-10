import { CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react'

interface StatusIconProps {
  status: string
  size?: number
}

export default function StatusIcon({ status, size = 5 }: StatusIconProps) {
  const cls = `h-${size} w-${size}`
  switch (status) {
    case 'approved':
    case 'completed':
      return <CheckCircle className={`${cls} text-green-500`} />
    case 'failed':
    case 'rejected':
      return <XCircle className={`${cls} text-red-500`} />
    case 'in_progress':
      return <Loader2 className={`${cls} text-yellow-500 animate-spin`} />
    case 'awaiting_approval':
      return <Clock className={`${cls} text-blue-500`} />
    default:
      return <div className={`${cls} rounded-full border-2 border-gray-300`} />
  }
}
