import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Users, Plus, Trash2, Edit2, Loader2, AlertCircle, Crown, UserMinus, ChevronRight, X, Copy, Check, Link2 } from 'lucide-react'
import { workspacesApi } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import type { Workspace, WorkspaceDetail, Invite } from '@/types'
import { getErrorMessage } from '@/types'

export default function Workspaces() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
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

  // Invites state
  const [invites, setInvites] = useState<Invite[]>([])
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteExpiresHours, setInviteExpiresHours] = useState(72)
  const [isCreatingInvite, setIsCreatingInvite] = useState(false)
  const [deletingInviteId, setDeletingInviteId] = useState<number | null>(null)
  const [copiedInviteId, setCopiedInviteId] = useState<number | null>(null)

  useEffect(() => {
    fetchWorkspaces()
  }, [])

  // Load workspace detail when URL param changes
  useEffect(() => {
    if (id) {
      loadWorkspaceDetail(parseInt(id))
    } else {
      setSelectedWorkspace(null)
      setInvites([])
    }
  }, [id])

  const fetchWorkspaces = async () => {
    try {
      const response = await workspacesApi.list()
      setWorkspaces(response.data)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  const loadWorkspaceDetail = async (workspaceId: number) => {
    setIsLoadingDetail(true)
    try {
      const [detailRes, invitesRes] = await Promise.all([
        workspacesApi.get(workspaceId),
        workspacesApi.listInvites(workspaceId).catch(() => ({ data: [] }))
      ])
      setSelectedWorkspace(detailRes.data)
      setInvites(invitesRes.data || [])
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoadingDetail(false)
    }
  }

  const handleSelectWorkspace = (workspaceId: number | null) => {
    if (workspaceId === null) {
      navigate('/workspaces')
    } else {
      navigate(`/workspaces/${workspaceId}`)
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
      // Navigate to new workspace
      navigate(`/workspaces/${response.data.id}`)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
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
    } catch (err: unknown) {
      setError(getErrorMessage(err))
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
        navigate('/workspaces')
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err))
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
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setRemovingMemberId(null)
    }
  }

  // Invite handlers
  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedWorkspace) return

    setIsCreatingInvite(true)
    setError(null)

    try {
      const response = await workspacesApi.createInvite(selectedWorkspace.id, {
        email: inviteEmail || undefined,
        expires_in_hours: inviteExpiresHours
      })
      setInvites([response.data, ...invites])
      setShowInviteForm(false)
      setInviteEmail('')
      setInviteExpiresHours(72)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsCreatingInvite(false)
    }
  }

  const handleDeleteInvite = async (inviteId: number) => {
    if (!selectedWorkspace) return
    if (!confirm('Delete this invite?')) return

    setDeletingInviteId(inviteId)
    try {
      await workspacesApi.deleteInvite(selectedWorkspace.id, inviteId)
      setInvites(invites.filter(inv => inv.id !== inviteId))
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setDeletingInviteId(null)
    }
  }

  const copyInviteLink = async (invite: Invite) => {
    const baseUrl = window.location.origin
    const link = `${baseUrl}/register?invite=${invite.token}`
    try {
      await navigator.clipboard.writeText(link)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = link
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    setCopiedInviteId(invite.id)
    setTimeout(() => setCopiedInviteId(null), 2000)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  // Filter active/used invites
  const activeInvites = invites.filter(inv => inv.is_valid && !inv.used_at)
  const usedInvites = invites.filter(inv => inv.used_at || !inv.is_valid)

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
                    onClick={() => handleSelectWorkspace(ws.id)}
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
            <div className="space-y-6">
              {/* Workspace Info */}
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
                </div>
              </div>

              {/* Invites Section (owner only) */}
              {selectedWorkspace.is_owner && (
                <div className="bg-white rounded-lg shadow border">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <div className="flex items-center">
                      <Link2 className="h-5 w-5 text-gray-500 mr-2" />
                      <h3 className="font-semibold text-gray-900">Invites</h3>
                    </div>
                    <button
                      onClick={() => setShowInviteForm(true)}
                      className="flex items-center px-3 py-1.5 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Create Invite
                    </button>
                  </div>

                  {/* Create Invite Form */}
                  {showInviteForm && (
                    <div className="p-6 bg-gray-50 border-b">
                      <form onSubmit={handleCreateInvite} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Email (optional)
                            </label>
                            <input
                              type="email"
                              value={inviteEmail}
                              onChange={(e) => setInviteEmail(e.target.value)}
                              placeholder="user@example.com"
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                            />
                            <p className="mt-1 text-xs text-gray-500">
                              If set, only this email can use the invite
                            </p>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Expires in (hours)
                            </label>
                            <input
                              type="number"
                              value={inviteExpiresHours}
                              onChange={(e) => setInviteExpiresHours(Number(e.target.value))}
                              min={1}
                              max={720}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                            />
                          </div>
                        </div>
                        <div className="flex justify-end space-x-3">
                          <button
                            type="button"
                            onClick={() => {
                              setShowInviteForm(false)
                              setInviteEmail('')
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            disabled={isCreatingInvite}
                            className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
                          >
                            {isCreatingInvite && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            Create Invite
                          </button>
                        </div>
                      </form>
                    </div>
                  )}

                  {/* Invites List */}
                  <div className="p-6">
                    {invites.length === 0 ? (
                      <p className="text-center text-gray-500 py-4">
                        No invites yet. Create one to add members.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {/* Active invites */}
                        {activeInvites.length > 0 && (
                          <>
                            <p className="text-xs font-medium text-gray-500 uppercase">Active ({activeInvites.length})</p>
                            {activeInvites.map(invite => (
                              <div
                                key={invite.id}
                                className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-100"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center">
                                    <code className="text-sm font-mono text-gray-600 truncate mr-2">
                                      {invite.token.substring(0, 12)}...
                                    </code>
                                    {invite.email && (
                                      <span className="text-sm text-gray-500">for {invite.email}</span>
                                    )}
                                  </div>
                                  <p className="text-xs text-gray-500 mt-1">
                                    Expires {formatDateTime(invite.expires_at)}
                                  </p>
                                </div>
                                <div className="flex items-center space-x-1 ml-2">
                                  <button
                                    onClick={() => copyInviteLink(invite)}
                                    className="p-2 text-gray-500 hover:text-primary-600 hover:bg-white rounded"
                                    title="Copy invite link"
                                  >
                                    {copiedInviteId === invite.id ? (
                                      <Check className="h-4 w-4 text-green-500" />
                                    ) : (
                                      <Copy className="h-4 w-4" />
                                    )}
                                  </button>
                                  <button
                                    onClick={() => handleDeleteInvite(invite.id)}
                                    disabled={deletingInviteId === invite.id}
                                    className="p-2 text-gray-500 hover:text-red-600 hover:bg-white rounded"
                                    title="Delete invite"
                                  >
                                    {deletingInviteId === invite.id ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <Trash2 className="h-4 w-4" />
                                    )}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </>
                        )}

                        {/* Used/expired invites */}
                        {usedInvites.length > 0 && (
                          <>
                            <p className="text-xs font-medium text-gray-500 uppercase mt-4">
                              Used/Expired ({usedInvites.length})
                            </p>
                            {usedInvites.map(invite => (
                              <div
                                key={invite.id}
                                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg opacity-60"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center">
                                    <code className="text-sm font-mono text-gray-500 truncate mr-2">
                                      {invite.token.substring(0, 12)}...
                                    </code>
                                    {invite.email && (
                                      <span className="text-sm text-gray-400">for {invite.email}</span>
                                    )}
                                  </div>
                                  <p className="text-xs text-gray-400 mt-1">
                                    {invite.used_at ? (
                                      <span className="text-green-600">Used {formatDateTime(invite.used_at)}</span>
                                    ) : (
                                      <span className="text-red-500">Expired {formatDateTime(invite.expires_at)}</span>
                                    )}
                                  </p>
                                </div>
                                <button
                                  onClick={() => handleDeleteInvite(invite.id)}
                                  disabled={deletingInviteId === invite.id || !!invite.used_at}
                                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-white rounded disabled:opacity-50"
                                  title={invite.used_at ? "Can't delete used invite" : "Delete invite"}
                                >
                                  {deletingInviteId === invite.id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <Trash2 className="h-4 w-4" />
                                  )}
                                </button>
                              </div>
                            ))}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
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
