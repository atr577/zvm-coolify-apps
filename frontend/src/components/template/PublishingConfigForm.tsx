import { useState } from 'react'
import { Loader2, Save, Plus, X } from 'lucide-react'
import type { PublishingConfig } from '@/services/api'

interface PublishingConfigFormProps {
  config: PublishingConfig
  timezone: string
  onUpdate: (data: {
    enabled: boolean
    days: string[]
    preferred_times: string[]
    depth_days: number
  }) => Promise<void>
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

export function PublishingConfigForm({ config, timezone, onUpdate }: PublishingConfigFormProps) {
  const [days, setDays] = useState<string[]>(config.days)
  const [preferredTimes, setPreferredTimes] = useState<string[]>(
    config.preferred_times?.length ? config.preferred_times : ['18:00']
  )
  const [depthDays, setDepthDays] = useState(config.depth_days)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const hasChanges =
    JSON.stringify(days.sort()) !== JSON.stringify([...config.days].sort()) ||
    JSON.stringify(preferredTimes.sort()) !== JSON.stringify([...(config.preferred_times || ['18:00'])].sort()) ||
    depthDays !== config.depth_days

  const handleDayToggle = (day: string) => {
    setDays(prev =>
      prev.includes(day)
        ? prev.filter(d => d !== day)
        : [...prev, day]
    )
  }

  const handleAddTime = () => {
    if (preferredTimes.length < 4) {
      setPreferredTimes(prev => [...prev, '12:00'])
    }
  }

  const handleRemoveTime = (index: number) => {
    if (preferredTimes.length > 1) {
      setPreferredTimes(prev => prev.filter((_, i) => i !== index))
    }
  }

  const handleTimeChange = (index: number, value: string) => {
    setPreferredTimes(prev => prev.map((t, i) => i === index ? value : t))
  }

  const handleSave = async () => {
    if (!hasChanges) return

    try {
      setSaving(true)
      setError(null)
      setSuccess(false)

      // Auto-enable if days are configured, disable if empty
      await onUpdate({
        enabled: days.length > 0,
        days,
        preferred_times: preferredTimes,
        depth_days: depthDays
      })

      setSuccess(true)
      setTimeout(() => setSuccess(false), 2000)
    } catch (err) {
      setError('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Days Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Publishing Days
        </label>
        <div className="flex flex-wrap gap-2">
          {DAYS.map(day => (
            <button
              key={day.value}
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
        {days.length === 0 && (
          <p className="text-xs text-yellow-600 mt-1">Select at least one day</p>
        )}
      </div>

      {/* Times Selection */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Publishing Times
          </label>
          {preferredTimes.length < 4 && (
            <button
              onClick={handleAddTime}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
            >
              <Plus className="w-3 h-3" />
              Add time
            </button>
          )}
        </div>
        <div className="space-y-2">
          {preferredTimes.map((time, index) => (
            <div key={index} className="flex items-center gap-2">
              <input
                type="time"
                value={time}
                onChange={e => handleTimeChange(index, e.target.value)}
                className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {preferredTimes.length > 1 && (
                <button
                  onClick={() => handleRemoveTime(index)}
                  className="p-2 text-gray-400 hover:text-red-500"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Timezone: {timezone} • Up to 4 times per day
        </p>
      </div>

      {/* Depth Days */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Schedule Depth (days)
        </label>
        <input
          type="number"
          min={1}
          max={30}
          value={depthDays}
          onChange={e => setDepthDays(Math.max(1, Math.min(30, parseInt(e.target.value) || 7)))}
          className="w-full max-w-[200px] px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">How far ahead to show schedule</p>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Save Settings
        </button>

        {success && (
          <span className="text-sm text-green-600">Settings saved!</span>
        )}

        {error && (
          <span className="text-sm text-red-600">{error}</span>
        )}
      </div>
    </div>
  )
}
