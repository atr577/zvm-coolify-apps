import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Loader2 } from 'lucide-react'

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", color: '#1a1a1a', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', textAlign: 'center' }}>
        <div style={{ fontSize: 48, fontWeight: 800, letterSpacing: -1, marginBottom: 16 }}>REGGY</div>
        <p style={{ fontSize: 20, color: '#555', maxWidth: 560, marginBottom: 40, lineHeight: 1.5 }}>
          AI-powered platform for creating and publishing short-form viral videos to YouTube, Instagram, and TikTok.
        </p>

        <div style={{ display: 'flex', gap: 32, marginBottom: 48, flexWrap: 'wrap', justifyContent: 'center' }}>
          <div style={{ maxWidth: 200, textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#127916;</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>AI Video Generation</div>
            <div style={{ fontSize: 14, color: '#666' }}>Create videos from text prompts using state-of-the-art AI models</div>
          </div>
          <div style={{ maxWidth: 200, textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#127911;</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>AI Music</div>
            <div style={{ fontSize: 14, color: '#666' }}>Generate custom music tracks that match your video content</div>
          </div>
          <div style={{ maxWidth: 200, textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#128640;</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Auto Publishing</div>
            <div style={{ fontSize: 14, color: '#666' }}>Schedule and publish to multiple platforms automatically</div>
          </div>
        </div>

        <a
          href="/login"
          style={{ display: 'inline-block', background: '#1a1a1a', color: '#fff', padding: '14px 40px', borderRadius: 8, textDecoration: 'none', fontSize: 16, fontWeight: 600 }}
        >
          Sign In
        </a>
      </div>

      <footer style={{ padding: 24, textAlign: 'center', borderTop: '1px solid #eee', fontSize: 14, color: '#888' }}>
        <a href="/privacy" style={{ color: '#555', textDecoration: 'none', margin: '0 12px' }}>Privacy Policy</a>
        <a href="/terms" style={{ color: '#555', textDecoration: 'none', margin: '0 12px' }}>Terms of Service</a>
        <span>&copy; 2026 REGGY</span>
      </footer>
    </div>
  )
}
