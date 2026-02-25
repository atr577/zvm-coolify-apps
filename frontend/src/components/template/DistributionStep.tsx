import { ExternalLink } from 'lucide-react'
import type { SocialAccount } from '@/types'
import type { WorkspaceYouTubeAccount } from '@/services/api'

const COMMON_TIMEZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'America/New_York (UTC-5)' },
  { value: 'America/Chicago', label: 'America/Chicago (UTC-6)' },
  { value: 'America/Denver', label: 'America/Denver (UTC-7)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (UTC-8)' },
  { value: 'America/Toronto', label: 'America/Toronto (UTC-5)' },
  { value: 'America/Mexico_City', label: 'America/Mexico_City (UTC-6)' },
  { value: 'America/Sao_Paulo', label: 'America/Sao_Paulo (UTC-3)' },
  { value: 'Europe/London', label: 'Europe/London (UTC+0)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (UTC+1)' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin (UTC+1)' },
  { value: 'Europe/Moscow', label: 'Europe/Moscow (UTC+3)' },
  { value: 'Europe/Istanbul', label: 'Europe/Istanbul (UTC+3)' },
  { value: 'Asia/Dubai', label: 'Asia/Dubai (UTC+4)' },
  { value: 'Asia/Kolkata', label: 'Asia/Kolkata (UTC+5:30)' },
  { value: 'Asia/Bangkok', label: 'Asia/Bangkok (UTC+7)' },
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai (UTC+8)' },
  { value: 'Asia/Hong_Kong', label: 'Asia/Hong_Kong (UTC+8)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (UTC+9)' },
  { value: 'Asia/Seoul', label: 'Asia/Seoul (UTC+9)' },
  { value: 'Asia/Singapore', label: 'Asia/Singapore (UTC+8)' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney (UTC+11)' },
  { value: 'Pacific/Auckland', label: 'Pacific/Auckland (UTC+13)' },
  { value: 'Africa/Cairo', label: 'Africa/Cairo (UTC+2)' },
]

interface DistributionStepProps {
  projectId: number
  workspaceId: number | null
  boundAccounts: SocialAccount[]
  workspaceAccounts: SocialAccount[]
  workspaceYouTubeAccounts: WorkspaceYouTubeAccount[]
  boundYouTubeAccountId: number | null
  bindingLoading: string | null
  onBindAccount: (platform: string, accountId: number | null) => void
  onBindYouTubeAccount: (accountId: number | null) => void
  publishingConfig: {
    is_paused: boolean
    days: string[]
    preferred_times: string[]
    depth_days: number
  }
  onPublishingChange: (updates: Partial<{
    is_paused: boolean
    days: string[]
    preferred_times: string[]
    depth_days: number
  }>) => void
  timezone: string
  onTimezoneChange: (tz: string) => void
}

const DAYS = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' },
]

export function DistributionStep({
  boundAccounts,
  workspaceAccounts,
  workspaceYouTubeAccounts,
  boundYouTubeAccountId,
  bindingLoading,
  onBindAccount,
  onBindYouTubeAccount,
  publishingConfig,
  onPublishingChange,
  timezone,
  onTimezoneChange,
}: DistributionStepProps) {
  const { days, preferred_times: preferredTimes, depth_days: depthDays, is_paused: isPaused } = publishingConfig

  const getBoundAccount = (platform: string) =>
    boundAccounts.find((acc) => acc.platform === platform && acc.is_active)

  const handleDayToggle = (day: string) => {
    onPublishingChange({
      days: days.includes(day) ? days.filter((d) => d !== day) : [...days, day],
    })
  }

  const handleAddTime = () => {
    if (preferredTimes.length < 4) {
      onPublishingChange({ preferred_times: [...preferredTimes, '12:00'] })
    }
  }

  const handleRemoveTime = (index: number) => {
    if (preferredTimes.length > 1) {
      onPublishingChange({
        preferred_times: preferredTimes.filter((_, i) => i !== index),
      })
    }
  }

  const handleTimeChange = (index: number, value: string) => {
    onPublishingChange({
      preferred_times: preferredTimes.map((t, i) => (i === index ? value : t)),
    })
  }

  return (
    <div className="space-y-6">
      {/* Social Accounts */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Social Accounts</h4>
        <div className="space-y-3">
          {['instagram', 'tiktok', 'youtube'].map((platform) => {
            const platformAccounts = workspaceAccounts.filter(
              (a) => a.platform === platform && a.is_active
            )
            const bound = getBoundAccount(platform)
            const isLoading = bindingLoading === platform
            const wsYtAccounts = platform === 'youtube' ? workspaceYouTubeAccounts : []
            const totalAccounts = platformAccounts.length + wsYtAccounts.length

            // For YouTube: resolve current value (personal or workspace)
            const youtubeValue = platform === 'youtube'
              ? (bound ? String(bound.id) : boundYouTubeAccountId ? `ws:${boundYouTubeAccountId}` : '')
              : ''

            return (
              <div key={platform} className="border rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">{platform}</span>
                  {isLoading && <span className="text-xs text-gray-400">...</span>}
                </div>
                {totalAccounts === 0 ? (
                  <p className="text-xs text-gray-400 mt-1">No connected accounts</p>
                ) : platform === 'youtube' ? (
                  <select
                    value={youtubeValue}
                    onChange={(e) => {
                      const val = e.target.value
                      if (!val) {
                        // Deselect: clear both
                        if (bound) onBindAccount(platform, null)
                        if (boundYouTubeAccountId) onBindYouTubeAccount(null)
                      } else if (val.startsWith('ws:')) {
                        onBindYouTubeAccount(parseInt(val.slice(3)))
                      } else {
                        onBindAccount(platform, Number(val))
                      }
                    }}
                    disabled={isLoading}
                    className="w-full mt-2 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    <option value="">Not selected</option>
                    {platformAccounts.length > 0 && (
                      <optgroup label="Personal">
                        {platformAccounts.map((acc) => (
                          <option key={acc.id} value={acc.id} disabled={acc.is_token_expired}>
                            {acc.display_name || acc.username || acc.platform_user_id}
                            {acc.is_token_expired ? ' (expired)' : ''}
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {wsYtAccounts.length > 0 && (
                      <optgroup label="Workspace">
                        {wsYtAccounts.map((acc) => (
                          <option key={`ws:${acc.id}`} value={`ws:${acc.id}`}>
                            {acc.channel_handle || acc.channel_title} [Workspace]
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                ) : (
                  <select
                    value={bound?.id || ''}
                    onChange={(e) =>
                      onBindAccount(
                        platform,
                        e.target.value ? Number(e.target.value) : null
                      )
                    }
                    disabled={isLoading}
                    className="w-full mt-2 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    <option value="">Not selected</option>
                    {platformAccounts.map((acc) => (
                      <option
                        key={acc.id}
                        value={acc.id}
                        disabled={acc.is_token_expired}
                      >
                        @{acc.username || acc.display_name || acc.platform_user_id}
                        {acc.is_token_expired ? ' (expired)' : ''}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )
          })}
        </div>
        <button
          type="button"
          onClick={() => window.open('/social-accounts', '_blank')}
          className="mt-3 flex items-center text-sm text-primary-600 hover:text-primary-700"
        >
          <ExternalLink className="h-3 w-3 mr-1" />
          Connect new account
        </button>
      </div>

      {/* Publishing Schedule */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Publishing Schedule</h4>

        {/* Days */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Publishing Days
          </label>
          <div className="flex flex-wrap gap-2">
            {DAYS.map((day) => (
              <button
                key={day.value}
                type="button"
                onClick={() => handleDayToggle(day.value)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md border transition ${
                  days.includes(day.value)
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                }`}
              >
                {day.label}
              </button>
            ))}
          </div>
        </div>

        {/* Times */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">
              Publishing Times
            </label>
            {preferredTimes.length < 4 && (
              <button
                type="button"
                onClick={handleAddTime}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                + Add time
              </button>
            )}
          </div>
          <div className="space-y-2">
            {preferredTimes.map((time, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="time"
                  value={time}
                  onChange={(e) => handleTimeChange(index, e.target.value)}
                  className="flex-1 max-w-[200px] px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                {preferredTimes.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveTime(index)}
                    className="p-2 text-gray-400 hover:text-red-500"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <label className="text-xs text-gray-500 shrink-0">Timezone:</label>
            <select
              value={timezone}
              onChange={(e) => onTimezoneChange(e.target.value)}
              className="text-xs px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>{tz.label}</option>
              ))}
            </select>
            <span className="text-xs text-gray-400">· Up to 4 times per day</span>
          </div>
        </div>

        {/* Depth */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Schedule Depth (days)
          </label>
          <input
            type="number"
            min={1}
            max={30}
            value={depthDays}
            onChange={(e) =>
              onPublishingChange({
                depth_days: Math.max(1, Math.min(30, parseInt(e.target.value) || 7)),
              })
            }
            className="w-full max-w-[200px] px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">How far ahead to show schedule</p>
        </div>

        {/* Active toggle */}
        <div className="flex items-center gap-3 pt-2 border-t">
          <label className="flex items-center gap-2 cursor-pointer">
            <button
              type="button"
              onClick={() => onPublishingChange({ is_paused: !isPaused })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                !isPaused ? 'bg-green-500' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                  !isPaused ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className="text-sm text-gray-700">
              {isPaused ? 'Publishing inactive' : 'Publishing active'}
            </span>
          </label>
        </div>
      </div>
    </div>
  )
}
