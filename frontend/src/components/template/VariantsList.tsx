import { useState, useEffect, useCallback } from 'react'
import { templateApi } from '@/services/api'
import type { Variant } from '@/types'

interface VariantsListProps {
  projectId: number
  refreshTrigger?: number
}

export function VariantsList({ projectId, refreshTrigger }: VariantsListProps) {
  const [variants, setVariants] = useState<Variant[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Pagination
  const [offset, setOffset] = useState(0)
  const limit = 20

  // Search
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  // Inline editing
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingData, setEditingData] = useState<Record<string, string>>({})

  const loadVariants = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await templateApi.listVariants(projectId, {
        search: search || undefined,
        offset,
        limit,
      })
      setVariants(response.data.variants)
      setTotal(response.data.total)
      if (response.data.csv_columns) {
        setColumns(response.data.csv_columns)
      }
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to load variants'
        : 'Failed to load variants'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [projectId, search, offset, limit])

  useEffect(() => {
    loadVariants()
  }, [loadVariants, refreshTrigger])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setOffset(0)
    setSearch(searchInput)
  }

  const handleEdit = (variant: Variant) => {
    setEditingId(variant.id)
    setEditingData({ ...variant.data })
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditingData({})
  }

  const handleSaveEdit = async (variantId: number) => {
    try {
      await templateApi.updateVariant(projectId, variantId, { data: editingData })
      setEditingId(null)
      setEditingData({})
      loadVariants()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update'
        : 'Failed to update'
      alert(errorMsg)
    }
  }

  const handleDelete = async (variantId: number) => {
    if (!confirm('Delete this variant?')) return
    try {
      await templateApi.deleteVariant(projectId, variantId)
      loadVariants()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete'
        : 'Failed to delete'
      alert(errorMsg)
    }
  }

  const handleDeleteAll = async () => {
    if (!confirm(`Delete all ${total} variants? This cannot be undone.`)) return
    try {
      await templateApi.deleteAllVariants(projectId)
      setVariants([])
      setTotal(0)
      setColumns([])
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete'
        : 'Failed to delete'
      alert(errorMsg)
    }
  }

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  if (loading && variants.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <svg className="animate-spin h-6 w-6 text-gray-400" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    )
  }

  if (total === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No variants uploaded yet. Upload a CSV file to get started.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with search and delete all */}
      <div className="flex items-center justify-between gap-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search variants..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            Search
          </button>
        </form>
        <button
          onClick={handleDeleteAll}
          className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
        >
          Delete All
        </button>
      </div>

      {/* Stats */}
      <div className="text-sm text-gray-500">
        {total} variants total
        {search && ` (filtered by "${search}")`}
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  #
                </th>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {col}
                  </th>
                ))}
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Used
                </th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {variants.map((variant) => (
                <tr key={variant.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-sm text-gray-500">
                    {variant.row_number}
                  </td>
                  {columns.map((col) => (
                    <td key={col} className="px-3 py-2 text-sm text-gray-900">
                      {editingId === variant.id ? (
                        <input
                          type="text"
                          value={editingData[col] || ''}
                          onChange={(e) => setEditingData({ ...editingData, [col]: e.target.value })}
                          className="w-full px-2 py-1 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        />
                      ) : (
                        <span className="max-w-xs truncate block">
                          {variant.data[col] || '—'}
                        </span>
                      )}
                    </td>
                  ))}
                  <td className="px-3 py-2 text-sm text-gray-500">
                    {variant.usage_count}
                  </td>
                  <td className="px-3 py-2 text-sm text-right whitespace-nowrap">
                    {editingId === variant.id ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleSaveEdit(variant.id)}
                          className="text-green-600 hover:text-green-800"
                        >
                          Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="text-gray-500 hover:text-gray-700"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEdit(variant)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(variant.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={currentPage >= totalPages}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
