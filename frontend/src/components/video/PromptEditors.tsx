import { Edit2, RotateCcw } from 'lucide-react'

// Image Prompt Editor
interface ImagePromptEditorProps {
  promptData: any
  editedPrompt: { main_prompt: string; negative_prompt: string; style_suffix: string } | null
  setEditedPrompt: (v: any) => void
  disabled: boolean
}

export function ImagePromptEditor({ promptData, editedPrompt, setEditedPrompt, disabled }: ImagePromptEditorProps) {
  return (
    <div className="border rounded-lg bg-gray-50">
      <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
        <span className="text-sm font-medium text-gray-700">
          Image Prompt for KLING
        </span>
        {editedPrompt && (
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
              <Edit2 className="h-3 w-3 mr-1" />
              Modified
            </span>
            <button
              onClick={() => setEditedPrompt(null)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              <RotateCcw className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
      <div className="p-3 space-y-3">
        <div>
          <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
            Main Prompt
          </label>
          <textarea
            value={editedPrompt?.main_prompt ?? promptData.main_prompt ?? ''}
            onChange={(e) => setEditedPrompt({
              main_prompt: e.target.value,
              negative_prompt: editedPrompt?.negative_prompt ?? promptData.negative_prompt ?? '',
              style_suffix: editedPrompt?.style_suffix ?? promptData.style_suffix ?? ''
            })}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
            rows={5}
            disabled={disabled}
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
            Negative Prompt
          </label>
          <textarea
            value={editedPrompt?.negative_prompt ?? promptData.negative_prompt ?? ''}
            onChange={(e) => setEditedPrompt({
              main_prompt: editedPrompt?.main_prompt ?? promptData.main_prompt ?? '',
              negative_prompt: e.target.value,
              style_suffix: editedPrompt?.style_suffix ?? promptData.style_suffix ?? ''
            })}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-red-700"
            rows={2}
            disabled={disabled}
            placeholder="e.g. blurry, low quality, watermark..."
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
            Style Suffix
          </label>
          <textarea
            value={editedPrompt?.style_suffix ?? promptData.style_suffix ?? ''}
            onChange={(e) => setEditedPrompt({
              main_prompt: editedPrompt?.main_prompt ?? promptData.main_prompt ?? '',
              negative_prompt: editedPrompt?.negative_prompt ?? promptData.negative_prompt ?? '',
              style_suffix: e.target.value
            })}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
            rows={2}
            disabled={disabled}
            placeholder="e.g. cinematic, 8k, professional lighting..."
          />
        </div>
      </div>
    </div>
  )
}

// Video Prompt Editor
interface VideoPromptEditorProps {
  scenarioData: any
  editedPrompt: { motion_prompt: string } | null
  setEditedPrompt: (v: any) => void
  disabled: boolean
}

export function VideoPromptEditor({ scenarioData, editedPrompt, setEditedPrompt, disabled }: VideoPromptEditorProps) {
  return (
    <div className="border rounded-lg bg-gray-50">
      <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
        <span className="text-sm font-medium text-gray-700">
          Video Motion Prompt for KLING
        </span>
        {editedPrompt && (
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
              <Edit2 className="h-3 w-3 mr-1" />
              Modified
            </span>
            <button
              onClick={() => setEditedPrompt(null)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              <RotateCcw className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
      <div className="p-3 space-y-3">
        <div>
          <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
            Motion Prompt
          </label>
          <textarea
            value={editedPrompt?.motion_prompt ?? scenarioData.motion_prompt ?? ''}
            onChange={(e) => setEditedPrompt({ motion_prompt: e.target.value })}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
            rows={4}
            disabled={disabled}
          />
        </div>
        {scenarioData.camera_movement && (
          <div>
            <label className="text-xs font-semibold text-gray-600 uppercase mb-1 block">
              Camera Movement (info)
            </label>
            <pre className="text-xs bg-white p-3 rounded border overflow-x-auto whitespace-pre-wrap text-gray-500">
              {typeof scenarioData.camera_movement === 'object'
                ? JSON.stringify(scenarioData.camera_movement, null, 2)
                : scenarioData.camera_movement}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
