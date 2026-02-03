import { CsvUpload } from './CsvUpload'
import { VariantsList } from './VariantsList'
import type { CSVUploadResponse } from '@/types'

interface InputStepProps {
  projectId: number
  refreshTrigger: number
  onCsvUploadSuccess: (response: CSVUploadResponse) => void
}

export function InputStep({ projectId, refreshTrigger, onCsvUploadSuccess }: InputStepProps) {
  return (
    <div className="space-y-4">
      <CsvUpload projectId={projectId} onUploadSuccess={onCsvUploadSuccess} />
      <VariantsList projectId={projectId} refreshTrigger={refreshTrigger} />
    </div>
  )
}
