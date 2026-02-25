import { useEffect, useState } from 'react'
import { Youtube, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

type PageState = 'idle' | 'loading' | 'success' | 'error'

const ERROR_MESSAGES: Record<string, string> = {
  access_denied: 'Access was denied. Please try again and grant REGGY access to your YouTube account.',
  no_refresh_token: 'Authorization incomplete. Please revoke REGGY access in your Google Account settings (myaccount.google.com/permissions), then try again.',
  no_channel: 'No YouTube channel found on this account. Create one at youtube.com, then try again.',
  already_linked: 'This YouTube channel is already linked to REGGY.',
  invalid_state: 'Session expired. Please try again.',
  config_error: 'Configuration error. Please contact support.',
  unknown: 'Something went wrong. Please try again.',
}

export default function LinkYouTubePage() {
  const [state, setState] = useState<PageState>('idle')
  const [email, setEmail] = useState('')
  const [channel, setChannel] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const status = params.get('status')

    if (status === 'success') {
      setEmail(params.get('email') || '')
      setChannel(params.get('channel') || '')
      setState('success')
    } else if (status === 'error') {
      const reason = params.get('reason') || 'unknown'
      setErrorMsg(ERROR_MESSAGES[reason] || ERROR_MESSAGES.unknown)
      setState('error')
    }
  }, [])

  const handleLink = () => {
    setState('loading')
    window.location.href = '/api/link-youtube/start'
  }

  const handleRetry = () => {
    window.location.href = '/link-youtube-account'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <div className="bg-purple-600 p-4 rounded-2xl">
            <Youtube className="h-10 w-10 text-white" />
          </div>
        </div>

        {state === 'idle' && (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              Link your YouTube account
            </h1>
            <p className="text-gray-500 mb-8">
              Connect your YouTube channel to REGGY so we can publish videos on your behalf.
            </p>
            <button
              onClick={handleLink}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition"
            >
              <Youtube className="h-5 w-5" />
              Link YouTube Account
            </button>
          </>
        )}

        {state === 'loading' && (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              Redirecting to Google...
            </h1>
            <div className="flex justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
            </div>
          </>
        )}

        {state === 'success' && (
          <>
            <div className="flex justify-center mb-4">
              <CheckCircle className="h-16 w-16 text-green-500" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              Account linked!
            </h1>
            <p className="text-gray-600 mb-2">
              <span className="font-medium">{channel}</span>
            </p>
            <p className="text-gray-400 text-sm mb-6">{email}</p>
            <p className="text-gray-500">You can close this tab.</p>
          </>
        )}

        {state === 'error' && (
          <>
            <div className="flex justify-center mb-4">
              <AlertCircle className="h-16 w-16 text-red-500" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              Something went wrong
            </h1>
            <p className="text-gray-600 mb-8">{errorMsg}</p>
            <button
              onClick={handleRetry}
              className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition"
            >
              Try again
            </button>
          </>
        )}
      </div>
    </div>
  )
}
