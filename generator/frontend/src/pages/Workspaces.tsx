import { useState, useEffect } from 'react'
import { Users, Plus, Trash2, Edit2, Loader2, AlertCircle, Crown, UserMinus, ChevronRight, X } from 'lucide-react'
import { workspacesApi } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import type { Workspace, WorkspaceDetail } from '@/types'

export default function Workspaces() {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Create workspace form
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createName, setCreateName] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  // Edit workspace
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [removingMemberId, setRemovingMemberId] = useState<number | null>(null)

  useEffect(() => {
    fetchWorkspaces()
  }, [])

  const fetchWorkspaces = async () => {
    try {
      const response = await workspacesApi.list()
      setWorkspaces(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load workspaces')
    } finally {
      setIsLoading(false)
    }
  }

  const loadWorkspaceDetail = async (workspaceId: number) => {
    setIsLoadingDetail(true)
    try {
      const response = await workspacesApi.get(workspaceId)
      setSelectedWorkspace(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load workspace details')
    } finally {
      setIsLoadingDetail(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createName.trim()) return

    setIsCreating(true)
    setError(null)

    try {
      const response = await workspacesApi.create({ name: createName.trim() })
      setWorkspaces([...workspaces, response.data])
      setShowCreateForm(false)
      setCreateName('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create workspace')
    } finally {
      setIsCreating(false)
    }
  }

  const handleUpdate = async (workspaceId: number) => {
    if (!editName.trim()) return

    setIsSaving(true)
    setError(null)

    try {
      const response = await workspacesApi.update(workspaceId, { name: editName.trim() })
      setWorkspaces(workspaces.map(ws => ws.id === workspaceId ? response.data : ws))
      if (selectedWorkspace?.id === workspaceId) {
        setSelectedWorkspace({ ...selectedWorkspace, name: response.data.name })
      }
      setEditingId(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update workspace')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (workspaceId: number) => {
    if (!confirm('Are you sure you want to delete this workspace? This cannot be undone.')) {
      return
    }

    setDeletingId(workspaceId)
    try {
      await workspacesApi.delete(workspaceId)
      setWorkspaces(workspaces.filter(ws => ws.id !== workspaceId))
      if (selectedWorkspace?.id === workspaceId) {
        setSelectedWorkspace(null)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete workspace')
    } finally {
      setDeletingId(null)
    }
  }

  const handleRemoveMember = async (userId: number) => {
    if (!selectedWorkspace) return
    if (!confirm('Are you sure you want to remove this member?')) return

    setRemovingMemberId(userId)
    try {
      await workspacesApi.removeMember(selectedWorkspace.id, userId)
      setSelectedWorkspace({
        ...selectedWorkspace,
        members: selectedWorkspace.members.filter(m => m.user_id !== userId)
      })
      // Update member count in list
      setWorkspaces(workspaces.map(ws =>
        ws.id === selectedWorkspace.id
          ? { ...ws, member_count: (ws.member_count || 1) - 1 }
          : ws
      ))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove member')
    } finally {
      setRemovingMemberId(null)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workspaces</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your workspaces and team members.
          </p>
        </div>
        {user?.can_create_workspace && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Workspace
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-sm text-red-600 underline mt-1"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Create Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Workspace</h3>
          <form onSubmit={handleCreate} className="flex items-end space-x-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Workspace Name
              </label>
              <input
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="My Workspace"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                autoFocus
              />
            </div>
            <button
              type="button"
              onClick={() => {
                setShowCreateForm(false)
                setCreateName('')
              }}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating || !createName.trim()}
              className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isCreating && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Create
            </button>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workspace List */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow border">
            <div className="px-4 py-3 border-b">
              <h3 className="font-semibold text-gray-900">Your Workspaces</h3>
            </div>
            <div className="divide-y">
              {workspaces.length === 0 ? (
                <p className="p-4 text-sm text-gray-500 text-center">
                  No workspaces yet.
                </p>
              ) : (
                workspaces.map(ws => (
                  <div
                    key={ws.id}
                    className={`p-4 cursor-pointer hover:bg-gray-50 ${
                      selectedWorkspace?.id === ws.id ? 'bg-primary-50 border-l-4 border-primary-500' : ''
                    }`}
                    onClick={() => loadWorkspaceDetail(ws.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center min-w-0">
                        <Users className="h-5 w-5 text-gray-400 mr-3 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="flex items-center">
                            <p className="font-medium text-gray-900 truncate">{ws.name}</p>
                            {ws.is_owner && (
                              <span title="You own this workspace">
                                <Crown className="h-4 w-4 text-yellow-500 ml-2" />
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500">
                            {ws.member_count || 1} member{(ws.member_count || 1) > 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Workspace Detail */}
        <div className="lg:col-span-2">
          {isLoadingDetail ? (
            <div className="bg-white rounded-lg shadow border p-8 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
          ) : selectedWorkspace ? (
            <div className="bg-white rounded-lg shadow border">
              <div className="px-6 py-4 border-b flex items-center justify-between">
                <div>
                  {editingId === selectedWorkspace.id ? (
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                        autoFocus
                      />
                      <button
                        onClick={() => handleUpdate(selectedWorkspace.id)}
                        disabled={isSaving}
                        className="p-1 text-green-600 hover:bg-green-50 rounded"
                      >
                        {isSaving ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Save'}
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1 text-gray-500 hover:bg-gray-100 rounded"
                      >
                        <X className="h-5 w-5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <h2 className="text-xl font-semibold text-gray-900">{selectedWorkspace.name}</h2>
                      {selectedWorkspace.is_owner && (
                        <span title="You own this workspace">
                          <Crown className="h-5 w-5 text-yellow-500 ml-2" />
                        </span>
                      )}
                    </div>
                  )}
                  <p className="text-sm text-gray-500 mt-1">
                    Created {formatDate(selectedWorkspace.created_at)}
                  </p>
                </div>
                {selectedWorkspace.is_owner && editingId !== selectedWorkspace.id && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => {
                        setEditingId(selectedWorkspace.id)
                        setEditName(selectedWorkspace.name)
                      }}
                      className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded"
                      title="Edit workspace"
                    >
                      <Edit2 className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(selectedWorkspace.id)}
                      disabled={deletingId === selectedWorkspace.id}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                      title="Delete workspace"
                    >
                      {deletingId === selectedWorkspace.id ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <Trash2 className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                )}
              </div>

              {/* Members */}
              <div className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4">
                  Members ({selectedWorkspace.members.length})
                </h3>
                <div className="space-y-3">
                  {selectedWorkspace.members.map(member => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center">
                        <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                          <span className="text-primary-700 font-medium">
                            {(member.user?.full_name || member.user?.email || '?')[0].toUpperCase()}
                          </span>
                        </div>
                        <div className="ml-3">
                          <p className="font-medium text-gray-900">
                            {member.user?.full_name || member.user?.email || 'Unknown'}
                          </p>
                          <div className="flex items-center text-sm text-gray-500">
                            {member.user?.email && member.user?.full_name && (
                              <span className="mr-2">{member.user.email}</span>
                            )}
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              member.role === 'owner'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-600'
                            }`}>
                              {member.role}
                            </span>
                          </div>
                        </div>
                      </div>
                      {selectedWorkspace.is_owner && member.role !== 'owner' && (
                        <button
                          onClick={() => handleRemoveMember(member.user_id)}
                          disabled={removingMemberId === member.user_id}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                          title="Remove member"
                        >
                          {removingMemberId === member.user_id ? (
                            <Loader2 className="h-5 w-5 animate-spin" />
                          ) : (
                            <UserMinus className="h-5 w-5" />
                          )}
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                {selectedWorkspace.is_owner && (
                  <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-sm text-blue-800">
                      To add members to this workspace, create a <strong>Workspace Invite</strong> from the Settings page and select this workspace.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow border p-8 text-center text-gray-500">
              <Users className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a workspace to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
