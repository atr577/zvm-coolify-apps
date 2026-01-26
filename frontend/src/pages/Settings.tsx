import { useState, useEffect } from 'react'
import { Link2, Users, User, Trash2, Copy, Loader2, AlertCircle, Plus, Check } from 'lucide-react'
import { invitesApi, workspacesApi } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import type { Invite, Workspace, InviteType } from '@/types'
import { getErrorMessage } from '@/types'

const TABS = [
  { id: 'standalone', label: 'Standalone Invites', icon: User },
  { id: 'workspace', label: 'Workspace Invites', icon: Users },
]

export default function Settings() {
  const { isAdmin } = useAuth()
  const [activeTab, setActiveTab] = useState<InviteType>('standalone')
  const [invites, setInvites] = useState<Invite[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create invite form
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createEmail, setCreateEmail] = useState('')
  const [createWorkspaceId, setCreateWorkspaceId] = useState<number | ''>('')
  const [createExpiresHours, setCreateExpiresHours] = useState(72)
  const [isCreating, setIsCreating] = useState(false)

  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [invitesRes, workspacesRes] = await Promise.all([
        invitesApi.list(),
        workspacesApi.listAll()  // Admin endpoint to get all workspaces
      ])
      setInvites(invitesRes.data)
      setWorkspaces(workspacesRes.data)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsCreating(true)
    setError(null)

    try {
      const response = await invitesApi.create({
        type: activeTab,
        email: createEmail || undefined,
        workspace_id: activeTab === 'workspace' && createWorkspaceId ? Number(createWorkspaceId) : undefined,
        expires_in_hours: createExpiresHours
      })
      setInvites([response.data, ...invites])
      setShowCreateForm(false)
      setCreateEmail('')
      setCreateWorkspaceId('')
      setCreateExpiresHours(72)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsCreating(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this invite?')) {
      return
    }

    setDeletingId(id)
    try {
      await invitesApi.delete(id)
      setInvites(invites.filter(inv => inv.id !== id))
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  const copyInviteLink = async (invite: Invite) => {
    const baseUrl = window.location.origin
    const link = `${baseUrl}/register?invite=${invite.token}`
    try {
      await navigator.clipboard.writeText(link)
    } catch {
      // Fallback for HTTP (clipboard API requires HTTPS)
      const textarea = document.createElement('textarea')
      textarea.value = link
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    setCopiedId(invite.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const filteredInvites = invites.filter(inv => inv.type === activeTab)

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900">Access Denied</h2>
          <p className="text-gray-500 mt-2">You don't have permission to access this page.</p>
        </div>
      </div>
    )
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage user invites and system settings.
        </p>
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

      {/* Invites Section */}
      <div className="bg-white rounded-lg shadow border">
        <div className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Link2 className="h-5 w-5 text-gray-500 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">User Invites</h2>
            </div>
            <button
              onClick={() => setShowCreateForm(true)}
              className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Invite
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex -mb-px">
            {TABS.map(tab => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as InviteType)}
                  className={`flex items-center px-6 py-3 text-sm font-medium border-b-2 ${
                    isActive
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {tab.label}
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                    isActive ? 'bg-primary-100 text-primary-600' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {invites.filter(inv => inv.type === tab.id).length}
                  </span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* Create Form */}
        {showCreateForm && (
          <div className="p-6 bg-gray-50 border-b">
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email (optional)
                  </label>
                  <input
                    type="email"
                    value={createEmail}
                    onChange={(e) => setCreateEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    If specified, only this email can use the invite
                  </p>
                </div>

                {activeTab === 'workspace' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Workspace
                    </label>
                    <select
                      value={createWorkspaceId}
                      onChange={(e) => setCreateWorkspaceId(e.target.value ? Number(e.target.value) : '')}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="">Select workspace...</option>
                      {workspaces.map(ws => (
                        <option key={ws.id} value={ws.id}>{ws.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Expires in (hours)
                  </label>
                  <input
                    type="number"
                    value={createExpiresHours}
                    onChange={(e) => setCreateExpiresHours(Number(e.target.value))}
                    min={1}
                    max={720}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || (activeTab === 'workspace' && !createWorkspaceId)}
                  className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
                >
                  {isCreating && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  Create {activeTab === 'standalone' ? 'Standalone' : 'Workspace'} Invite
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Invites List */}
        <div className="p-6">
          {filteredInvites.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              No {activeTab} invites yet. Create one to get started.
            </p>
          ) : (
            <div className="space-y-3">
              {filteredInvites.map(invite => (
                <div
                  key={invite.id}
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    !invite.is_valid ? 'bg-gray-50 opacity-60' : 'bg-white'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center">
                      <code className="text-sm font-mono text-gray-600 truncate mr-3">
                        {invite.token.substring(0, 16)}...
                      </code>
                      {invite.email && (
                        <span className="text-sm text-gray-500">
                          for {invite.email}
                        </span>
                      )}
                      {invite.workspace_name && (
                        <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                          {invite.workspace_name}
                        </span>
                      )}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {invite.used_at ? (
                        <span className="text-green-600">
                          Used on {formatDate(invite.used_at)}
                        </span>
                      ) : new Date(invite.expires_at) < new Date() ? (
                        <span className="text-red-600">
                          Expired on {formatDate(invite.expires_at)}
                        </span>
                      ) : (
                        <span>
                          Expires {formatDate(invite.expires_at)}
                        </span>
                      )}
                      {' | Created '}{formatDate(invite.created_at)}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 ml-4">
                    {invite.is_valid && !invite.used_at && (
                      <button
                        onClick={() => copyInviteLink(invite)}
                        className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded"
                        title="Copy invite link"
                      >
                        {copiedId === invite.id ? (
                          <Check className="h-5 w-5 text-green-500" />
                        ) : (
                          <Copy className="h-5 w-5" />
                        )}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(invite.id)}
                      disabled={deletingId === invite.id}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                      title="Delete invite"
                    >
                      {deletingId === invite.id ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <Trash2 className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">About Invite Types</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li><strong>Standalone:</strong> User gets their own workspace and can create projects independently.</li>
          <li><strong>Workspace:</strong> User joins an existing workspace and sees shared projects. Cannot create own workspace.</li>
        </ul>
      </div>
    </div>
  )
}
