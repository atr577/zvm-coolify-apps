import { IMAGE_MODELS, ASPECT_RATIOS } from '@/constants/models'
import type { ImageModel, AspectRatio } from '@/types'

interface ImageStepProps {
  imageModel: string
  aspectRatio: string
  imagePromptTemplate: string
  csvColumns: string[] | null
  onModelChange: (model: string) => void
  onAspectRatioChange: (ratio: string) => void
  onPromptChange: (prompt: string) => void
}

export function ImageStep({
  imageModel,
  aspectRatio,
  imagePromptTemplate,
  csvColumns,
  onModelChange,
  onAspectRatioChange,
  onPromptChange,
}: ImageStepProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Image Model
          </label>
          <select
            value={imageModel}
            onChange={(e) => onModelChange(e.target.value as ImageModel)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {IMAGE_MODELS.map((model) => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Aspect Ratio
          </label>
          <select
            value={aspectRatio}
            onChange={(e) => onAspectRatioChange(e.target.value as AspectRatio)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {ASPECT_RATIOS.map((ratio) => (
              <option key={ratio.value} value={ratio.value}>
                {ratio.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Image Prompt Template
        </label>
        <p className="text-xs text-gray-500 mb-2">
          Use <code className="bg-gray-100 px-1 rounded">{'{column_name}'}</code> placeholders and{' '}
          <code className="bg-gray-100 px-1 rounded">{'{preprocessed}'}</code> for LLM output
        </p>
        <textarea
          value={imagePromptTemplate}
          onChange={(e) => onPromptChange(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
          placeholder="Enter image prompt template..."
        />
      </div>

      {/* Placeholder hints */}
      {csvColumns && csvColumns.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            Available placeholders
          </label>
          <div className="flex flex-wrap gap-1.5">
            {csvColumns.map((col) => (
              <code
                key={col}
                className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs cursor-pointer hover:bg-gray-200 transition"
                onClick={() => navigator.clipboard.writeText(`{${col}}`)}
                title="Click to copy"
              >
                {`{${col}}`}
              </code>
            ))}
            <code
              className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs cursor-pointer hover:bg-blue-200 transition"
              onClick={() => navigator.clipboard.writeText('{preprocessed}')}
              title="Click to copy"
            >
              {'{preprocessed}'}
            </code>
          </div>
        </div>
      )}
    </div>
  )
}
