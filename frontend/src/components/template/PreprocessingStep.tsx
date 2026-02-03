import { LLM_MODELS } from '@/constants/models'
import type { LLMModel } from '@/types'

interface PreprocessingStepProps {
  llmModel: string
  preprocessingPrompt: string
  csvColumns: string[] | null
  onModelChange: (model: string) => void
  onPromptChange: (prompt: string) => void
}

export function PreprocessingStep({
  llmModel,
  preprocessingPrompt,
  csvColumns,
  onModelChange,
  onPromptChange,
}: PreprocessingStepProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          LLM Model
        </label>
        <select
          value={llmModel}
          onChange={(e) => onModelChange(e.target.value as LLMModel)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        >
          {LLM_MODELS.map((model) => (
            <option key={model.value} value={model.value}>
              {model.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preprocessing Prompt
        </label>
        <p className="text-xs text-gray-500 mb-2">
          Use <code className="bg-gray-100 px-1 rounded">{'{column_name}'}</code> placeholders from CSV columns
        </p>
        <textarea
          value={preprocessingPrompt}
          onChange={(e) => onPromptChange(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
          placeholder="Enter preprocessing prompt..."
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
          </div>
        </div>
      )}
    </div>
  )
}
