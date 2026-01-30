import { useState, useCallback } from 'react'
import { templateApi } from '@/services/api'
import type { CSVUploadResponse } from '@/types'

interface CsvUploadProps {
  projectId: number
  onUploadSuccess: (response: CSVUploadResponse) => void
  onError?: (error: string) => void
}

export function CsvUpload({ projectId, onUploadSuccess, onError }: CsvUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [preview, setPreview] = useState<CSVUploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFile(files[0])
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFile(files[0])
    }
  }, [])

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      const errorMsg = 'Please select a CSV file'
      setError(errorMsg)
      onError?.(errorMsg)
      return
    }

    setIsUploading(true)
    setError(null)
    setPreview(null)

    try {
      const response = await templateApi.uploadCsv(projectId, file)
      setPreview(response.data)
      onUploadSuccess(response.data)
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Upload failed'
        : 'Upload failed'
      setError(errorMsg)
      onError?.(errorMsg)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
          }
          ${isUploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="hidden"
          id="csv-upload"
          disabled={isUploading}
        />
        <label htmlFor="csv-upload" className="cursor-pointer">
          <div className="text-gray-500">
            {isUploading ? (
              <div className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Uploading...</span>
              </div>
            ) : (
              <>
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p className="mt-2 text-sm">
                  <span className="text-blue-600 hover:text-blue-500">Upload a CSV file</span>
                  {' '}or drag and drop
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  CSV with any columns (UTF-8, Windows-1251 supported)
                </p>
              </>
            )}
          </div>
        </label>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Preview Table */}
      {preview && (
        <div className="border rounded-lg overflow-hidden">
          <div className="bg-green-50 px-4 py-2 border-b">
            <span className="text-green-700 font-medium">
              {preview.variants_created} variants uploaded
            </span>
            <span className="text-gray-500 ml-2">
              ({preview.csv_columns.length} columns)
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    #
                  </th>
                  {preview.csv_columns.map((col) => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {preview.preview.map((row, idx) => (
                  <tr key={idx}>
                    <td className="px-3 py-2 text-sm text-gray-500">{idx + 1}</td>
                    {preview.csv_columns.map((col) => (
                      <td key={col} className="px-3 py-2 text-sm text-gray-900 max-w-xs truncate">
                        {row[col] || '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.variants_created > 5 && (
            <div className="bg-gray-50 px-4 py-2 border-t text-center text-sm text-gray-500">
              Showing first 5 of {preview.variants_created} variants
            </div>
          )}
        </div>
      )}
    </div>
  )
}
