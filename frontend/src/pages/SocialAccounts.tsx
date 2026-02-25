import { useState, useEffect } from 'react'
import { Instagram, Youtube, Trash2, RefreshCw, Plus, Loader2, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react'
import api, { youtubeAccountsApi } from '@/services/api'
import type { WorkspaceYouTubeAccount } from '@/services/api'
import { getErrorMessage } from '@/types'

interface SocialAccount {
  id: number
  platform: string
  platform_user_id: string
  username: string | null
  display_name: string | null
  profile_picture: string | null
  is_active: boolean
  created_at: string
  is_token_expired: boolean
}

const PLATFORMS = [
  {
    id: 'instagram',
    name: 'Instagram',
    icon: Instagram,
    color: 'bg-gradient-to-r from-purple-500 to-pink-500',
    description: 'Connect your Instagram Business account'
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    icon: () => (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
      </svg>
    ),
    color: 'bg-black',
    description: 'Connect your TikTok account'
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: Youtube,
    color: 'bg-red-600',
    description: 'Connect your YouTube channel'
  }
]

export default function SocialAccounts() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([])
  const [workspaceYouTubeAccounts, setWorkspaceYouTubeAccounts] = useState<WorkspaceYouTubeAccount[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [refreshingId, setRefreshingId] = useState<number | null>(null)

  useEffect(() => {
    fetchAccounts()
  }, [])

  const fetchAccounts = async () => {
    try {
      const [accountsRes, wsYtRes] = await Promise.all([
        api.get<SocialAccount[]>('/api/social-accounts/'),
        youtubeAccountsApi.workspaceList(),
      ])
      setAccounts(accountsRes.data)
      setWorkspaceYouTubeAccounts(wsYtRes.data)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  const handleConnect = async (platformId: string) => {
    setConnectingPlatform(platformId)
    try {
      const response = await api.get<{ authorization_url: string }>(`/api/oauth/connect/${platformId}`)
      window.location.href = response.data.authorization_url
    } catch (err: unknown) {
      setError(getErrorMessage(err))
      setConnectingPlatform(null)
    }
  }

  const handleDisconnect = async (accountId: number) => {
    if (!confirm('Are you sure you want to disconnect this account?')) {
      return
    }

    setDeletingId(accountId)
    try {
      await api.delete(`/api/social-accounts/${accountId}`)
      setAccounts(accounts.filter(a => a.id !== accountId))
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  const handleRefresh = async (accountId: number, platform: string) => {
    setRefreshingId(accountId)
    try {
      await api.post(`/api/oauth/refresh/${platform}/${accountId}`)
      await fetchAccounts()
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setRefreshingId(null)
    }
  }

  const getAccountsForPlatform = (platformId: string) => {
    return accounts.filter(a => a.platform === platformId)
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
        <h1 className="text-2xl font-bold text-gray-900">Social Accounts</h1>
        <p className="mt-1 text-sm text-gray-500">
          Connect your social media accounts to publish videos directly from the platform.
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

      <div className="grid gap-6">
        {PLATFORMS.map(platform => {
          const platformAccounts = getAccountsForPlatform(platform.id)
          const IconComponent = platform.icon

          return (
            <div key={platform.id} className="bg-white rounded-lg shadow border p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className={`${platform.color} p-3 rounded-lg text-white`}>
                    <IconComponent />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-gray-900">{platform.name}</h3>
                    <p className="text-sm text-gray-500">{platform.description}</p>
                  </div>
                </div>

                <button
                  onClick={() => handleConnect(platform.id)}
                  disabled={connectingPlatform === platform.id}
                  className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {connectingPlatform === platform.id ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Connect Account
                </button>
              </div>

              {platformAccounts.length > 0 ? (
                <div className="space-y-3">
                  {platformAccounts.map(account => (
                    <div
                      key={account.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center">
                        {account.profile_picture ? (
                          <img
                            src={account.profile_picture}
                            alt={account.display_name || account.username || 'Profile'}
                            className="h-10 w-10 rounded-full"
                          />
                        ) : (
                          <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                            <IconComponent className="h-5 w-5 text-gray-500" />
                          </div>
                        )}
                        <div className="ml-3">
                          <p className="font-medium text-gray-900">
                            {account.display_name || account.username || 'Unknown'}
                          </p>
                          {account.username && account.display_name !== account.username && (
                            <p className="text-sm text-gray-500">
                              {account.username.startsWith('@') ? account.username : `@${account.username}`}
                            </p>
                          )}
                        </div>
                        <div className="ml-4">
                          {account.is_token_expired ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Token Expired
                            </span>
                          ) : account.is_active ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Connected
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                              Inactive
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {account.is_token_expired && (
                          <button
                            onClick={() => handleRefresh(account.id, account.platform)}
                            disabled={refreshingId === account.id}
                            className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded"
                            title="Refresh token"
                          >
                            {refreshingId === account.id ? (
                              <Loader2 className="h-5 w-5 animate-spin" />
                            ) : (
                              <RefreshCw className="h-5 w-5" />
                            )}
                          </button>
                        )}
                        <button
                          onClick={() => handleDisconnect(account.id)}
                          disabled={deletingId === account.id}
                          className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                          title="Disconnect account"
                        >
                          {deletingId === account.id ? (
                            <Loader2 className="h-5 w-5 animate-spin" />
                          ) : (
                            <Trash2 className="h-5 w-5" />
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 italic">
                  No {platform.name} accounts connected yet.
                </p>
              )}
            </div>
          )
        })}
      </div>

      {workspaceYouTubeAccounts.length > 0 && (
        <div className="bg-white rounded-lg shadow border p-6">
          <div className="flex items-center mb-4">
            <div className="bg-red-600 p-3 rounded-lg text-white">
              <Youtube />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">YouTube — Workspace Channels</h3>
              <p className="text-sm text-gray-500">
                Channels linked via{' '}
                <a href="/link-youtube-account" target="_blank" className="text-primary-600 underline inline-flex items-center gap-1">
                  /link-youtube-account <ExternalLink className="h-3 w-3" />
                </a>
              </p>
            </div>
          </div>
          <div className="space-y-3">
            {workspaceYouTubeAccounts.map(acc => (
              <div key={acc.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  {acc.channel_thumbnail_url ? (
                    <img src={acc.channel_thumbnail_url} alt={acc.channel_title} className="h-10 w-10 rounded-full" />
                  ) : (
                    <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                      <Youtube className="h-5 w-5 text-gray-500" />
                    </div>
                  )}
                  <div className="ml-3">
                    <p className="font-medium text-gray-900">{acc.channel_title}</p>
                    <p className="text-sm text-gray-500">{acc.google_email}</p>
                  </div>
                  <div className="ml-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      acc.token_status === 'active'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {acc.token_status === 'active'
                        ? <><CheckCircle className="h-3 w-3 mr-1" />Connected</>
                        : <><AlertCircle className="h-3 w-3 mr-1" />Revoked</>}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">About OAuth Integration</h4>
        <p className="text-sm text-blue-700">
          To connect social accounts, you need to configure OAuth credentials in the backend:
        </p>
        <ul className="text-sm text-blue-700 mt-2 list-disc list-inside">
          <li>INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET</li>
          <li>TIKTOK_CLIENT_ID and TIKTOK_CLIENT_SECRET</li>
          <li>YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET</li>
        </ul>
      </div>
    </div>
  )
}
