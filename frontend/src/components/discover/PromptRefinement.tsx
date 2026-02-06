import { useState, useEffect, useCallback } from 'react'
import {
  Loader2, Check, HelpCircle, Bot, Pencil, RotateCcw, Sparkles,
} from 'lucide-react'
import { discoverApi } from '@/services/api'
import type { DiscoverRefinement, DiscoverRefinementBlock } from '@/types'
import { getErrorMessage } from '@/types'

const BLOCK_LABELS: Record<string, string> = {
  subject: 'Subject',
  action: 'Action',
  moment: 'Moment',
  environment: 'Environment',
  camera: 'Camera',
  lighting: 'Lighting',
  style: 'Style',
  format: 'Format',
  details: 'Details',
}

const BLOCK_ORDER = ['subject', 'action', 'moment', 'environment', 'camera', 'lighting', 'style', 'format', 'details']

interface Props {
  projectId: number
  onReady: (refinedPrompt: string) => void
  generating?: boolean
}

export function PromptRefinement({ projectId, onReady, generating = false }: Props) {
  const [refinement, setRefinement] = useState<DiscoverRefinement | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [compiling, setCompiling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingBlock, setEditingBlock] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [otherValues, setOtherValues] = useState<Record<string, string>>({})
  const [showPromptEditor, setShowPromptEditor] = useState(false)
  const [promptDraft, setPromptDraft] = useState('')

  const fetchRefinement = useCallback(async () => {
    try {
      const res = await discoverApi.getRefinement(projectId)
      setRefinement(res.data)
      if (res.data.refined_prompt) {
        setPromptDraft(res.data.refined_prompt)
        setShowPromptEditor(true)
      }
      setError(null)
    } catch (err: unknown) {
      const e = err as { response?: { status?: number } }
      if (e.response?.status === 404) {
        // No refinement yet — trigger analysis
        await analyzePrompt()
      } else {
        setError(getErrorMessage(err))
      }
    } finally {
      setLoading(false)
    }
  }, [projectId])

  const analyzePrompt = async () => {
    setAnalyzing(true)
    setError(null)
    try {
      const res = await discoverApi.analyzePrompt(projectId)
      setRefinement(res.data)
      setShowPromptEditor(false)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAnalyzing(false)
    }
  }

  const handleReanalyze = async () => {
    if (!confirm('Re-analyze will reset all your block answers. Continue?')) return
    setLoading(true)
    setShowPromptEditor(false)
    try {
      await discoverApi.deleteRefinement(projectId)
      await analyzePrompt()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleAccept = async (blockName: string) => {
    if (!refinement) return
    const block = refinement.blocks[blockName]
    if (!block?.value) return
    try {
      const res = await discoverApi.updateBlock(projectId, blockName, block.value)
      setRefinement(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleSelectOption = async (blockName: string, option: string) => {
    try {
      const res = await discoverApi.updateBlock(projectId, blockName, option)
      setRefinement(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleOtherSubmit = async (blockName: string) => {
    const value = otherValues[blockName]?.trim()
    if (!value) return
    try {
      const res = await discoverApi.updateBlock(projectId, blockName, value)
      setRefinement(res.data)
      setOtherValues(prev => ({ ...prev, [blockName]: '' }))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleEditSave = async (blockName: string) => {
    if (!editValue.trim()) return
    try {
      const res = await discoverApi.updateBlock(projectId, blockName, editValue.trim())
      setRefinement(res.data)
      setEditingBlock(null)
      setEditValue('')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleCompile = async () => {
    setCompiling(true)
    setError(null)
    try {
      const res = await discoverApi.compilePrompt(projectId)
      setPromptDraft(res.data.refined_prompt)
      setShowPromptEditor(true)
      // Refresh full refinement
      const updated = await discoverApi.getRefinement(projectId)
      setRefinement(updated.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setCompiling(false)
    }
  }

  const handlePromptSave = async () => {
    if (!promptDraft.trim()) return
    try {
      const res = await discoverApi.updatePrompt(projectId, promptDraft.trim())
      setRefinement(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleGenerate = () => {
    if (refinement?.ready_to_generate && refinement.refined_prompt) {
      onReady(refinement.refined_prompt)
    }
  }

  useEffect(() => {
    fetchRefinement()
  }, [fetchRefinement])

  if (loading || analyzing) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <p className="text-sm text-gray-500">
          {analyzing ? 'Analyzing your concept...' : 'Loading...'}
        </p>
      </div>
    )
  }

  if (!refinement) {
    return (
      <div className="text-center py-8 text-red-500">
        {error || 'Failed to load refinement'}
      </div>
    )
  }

  const relevantBlocks = BLOCK_ORDER.filter(b => refinement.relevant_blocks.includes(b))

  return (
    <div className="space-y-4">
      {/* Header + Score */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Prompt Refinement</h3>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">{refinement.score}%</span>
          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                refinement.score >= 80 ? 'bg-green-500' : refinement.score >= 50 ? 'bg-yellow-500' : 'bg-red-400'
              }`}
              style={{ width: `${refinement.score}%` }}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Blocks */}
      {!showPromptEditor && (
        <div className="space-y-3">
          {relevantBlocks.map(blockName => {
            const block = refinement.blocks[blockName]
            if (!block) return null
            return (
              <BlockCard
                key={blockName}
                name={blockName}
                block={block}
                isEditing={editingBlock === blockName}
                editValue={editValue}
                otherValue={otherValues[blockName] || ''}
                onAccept={() => handleAccept(blockName)}
                onSelectOption={(opt) => handleSelectOption(blockName, opt)}
                onOtherChange={(val) => setOtherValues(prev => ({ ...prev, [blockName]: val }))}
                onOtherSubmit={() => handleOtherSubmit(blockName)}
                onEditStart={() => { setEditingBlock(blockName); setEditValue(block.value || '') }}
                onEditChange={setEditValue}
                onEditSave={() => handleEditSave(blockName)}
                onEditCancel={() => { setEditingBlock(null); setEditValue('') }}
              />
            )
          })}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleReanalyze}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RotateCcw className="w-4 h-4" />
              Re-analyze
            </button>
            <button
              onClick={handleCompile}
              disabled={refinement.score < 80 || compiling}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {compiling ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              Compile Prompt
            </button>
          </div>
        </div>
      )}

      {/* Final Prompt Editor */}
      {showPromptEditor && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700">Final Prompt</h4>
            <button
              onClick={() => setShowPromptEditor(false)}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Back to blocks
            </button>
          </div>
          <textarea
            value={promptDraft}
            onChange={e => setPromptDraft(e.target.value)}
            onBlur={handlePromptSave}
            rows={6}
            className="w-full p-3 border border-gray-300 rounded-lg text-sm resize-y focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            onClick={handleGenerate}
            disabled={!refinement.ready_to_generate || generating}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {generating ? 'Generating...' : 'Generate Images'}
          </button>
        </div>
      )}
    </div>
  )
}


// --- Block Card ---

interface BlockCardProps {
  name: string
  block: DiscoverRefinementBlock
  isEditing: boolean
  editValue: string
  otherValue: string
  onAccept: () => void
  onSelectOption: (opt: string) => void
  onOtherChange: (val: string) => void
  onOtherSubmit: () => void
  onEditStart: () => void
  onEditChange: (val: string) => void
  onEditSave: () => void
  onEditCancel: () => void
}

function BlockCard({
  name, block, isEditing, editValue, otherValue,
  onAccept, onSelectOption, onOtherChange, onOtherSubmit,
  onEditStart, onEditChange, onEditSave, onEditCancel,
}: BlockCardProps) {
  const StatusIcon = {
    confirmed: Check,
    needs_input: HelpCircle,
    auto_generated: Bot,
    auto_filled: Pencil,
  }[block.status] || HelpCircle

  const statusColor = {
    confirmed: 'text-green-500',
    needs_input: 'text-yellow-500',
    auto_generated: 'text-gray-400',
    auto_filled: 'text-blue-500',
  }[block.status]

  const borderColor = {
    confirmed: 'border-green-200 bg-green-50/30',
    needs_input: 'border-yellow-200 bg-yellow-50/30',
    auto_generated: 'border-gray-200',
    auto_filled: 'border-blue-200 bg-blue-50/30',
  }[block.status]

  const isReadonly = name === 'format'

  return (
    <div className={`border rounded-lg p-3 ${borderColor}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {BLOCK_LABELS[name] || name}
        </span>
        <StatusIcon className={`w-4 h-4 ${statusColor}`} />
      </div>

      {/* Editing mode */}
      {isEditing && (
        <div className="space-y-2">
          <textarea
            value={editValue}
            onChange={e => onEditChange(e.target.value)}
            rows={2}
            className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={onEditSave}
              className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
            >
              Save
            </button>
            <button
              onClick={onEditCancel}
              className="px-3 py-1 text-xs text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Needs input — show question + options */}
      {!isEditing && block.status === 'needs_input' && (
        <div className="space-y-2">
          {block.question && (
            <p className="text-sm text-gray-600">{block.question}</p>
          )}
          {block.options?.map((opt, i) => (
            <button
              key={i}
              onClick={() => onSelectOption(opt)}
              className="block w-full text-left px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
            >
              {opt}
            </button>
          ))}
          <div className="flex gap-2">
            <input
              type="text"
              value={otherValue}
              onChange={e => onOtherChange(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && onOtherSubmit()}
              placeholder="Other..."
              className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            {otherValue.trim() && (
              <button
                onClick={onOtherSubmit}
                className="px-3 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                OK
              </button>
            )}
          </div>
        </div>
      )}

      {/* Has value — show value + actions */}
      {!isEditing && block.status !== 'needs_input' && (
        <div>
          <p className="text-sm text-gray-800 mb-2">{block.value}</p>
          {!isReadonly && (
            <div className="flex gap-2">
              {block.status !== 'confirmed' && (
                <button
                  onClick={onAccept}
                  className="px-3 py-1 text-xs font-medium text-green-700 border border-green-300 rounded hover:bg-green-50"
                >
                  Accept
                </button>
              )}
              <button
                onClick={onEditStart}
                className="px-3 py-1 text-xs text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
              >
                Edit
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
