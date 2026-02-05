import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ProjectEdit from './pages/ProjectEdit'
import CreateVideo from './pages/CreateVideo'
import VideoDetail from './pages/VideoDetail'
import Login from './pages/Login'
import Register from './pages/Register'
import SocialAccounts from './pages/SocialAccounts'
import Analytics from './pages/Analytics'
import Workspaces from './pages/Workspaces'
import DiscoverPage from './pages/DiscoverPage'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/project/:id/edit" element={<ProjectEdit />} />
                <Route path="/project/:projectId/create-video" element={<CreateVideo />} />
                <Route path="/video/:id" element={<VideoDetail />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/social-accounts" element={<SocialAccounts />} />
                <Route path="/workspaces" element={<Workspaces />} />
                <Route path="/workspaces/:id" element={<Workspaces />} />
                <Route path="/discover/:id" element={<DiscoverPage />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
