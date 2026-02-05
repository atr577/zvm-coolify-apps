import { useMemo, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useSearchParams } from 'react-router-dom'
import { projectsApi, videosApi, workspacesApi, templateApi, discoverApi } from '@/services/api'
import type { Video, CreateProjectDto, Workspace, DiscoverProject } from '@/types'

export type FilterTab = 'all' | 'in_progress' | 'ready' | 'published' | 'errors'

const IN_PROGRESS_STATUSES = ['pending', 'in_progress', 'awaiting_approval', 'validating']
const ERROR_STATUSES = ['failed', 'validation_failed']

function isInProgress(status: string): boolean {
  return IN_PROGRESS_STATUSES.includes(status.toLowerCase())
}

function isError(status: string): boolean {
  return ERROR_STATUSES.includes(status.toLowerCase())
}

function isReady(video: Video): boolean {
  return video.status?.toLowerCase() === 'completed' && !video.is_published
}

function isPublished(video: Video): boolean {
  return video.is_published === true
}

export function useDashboardData() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  // Get state from URL params
  const selectedProjectId = searchParams.get('project') ? Number(searchParams.get('project')) : null
  const activeFilter = (searchParams.get('filter') as FilterTab) || 'all'

  // Update URL params
  const setSelectedProjectId = useCallback((id: number | null) => {
    setSearchParams(params => {
      if (id === null) params.delete('project')
      else params.set('project', String(id))
      return params
    })
  }, [setSearchParams])

  const setActiveFilter = useCallback((filter: FilterTab) => {
    setSearchParams(params => {
      if (filter === 'all') params.delete('filter')
      else params.set('filter', filter)
      return params
    })
  }, [setSearchParams])

  // Fetch projects
  const { data: projects, isLoading: projectsLoading } = useQuery(
    'projects',
    () => projectsApi.list().then(res => res.data.items)
  )

  // Fetch workspaces
  const { data: workspaces } = useQuery<Workspace[]>(
    'workspaces',
    () => workspacesApi.list().then(res => res.data)
  )

  // Fetch discover projects
  const { data: discoverProjects } = useQuery<DiscoverProject[]>(
    'discover-projects',
    () => discoverApi.list().then(res => res.data.projects)
  )

  // Fetch videos for all projects (and generation counts for template projects)
  const { data: allVideos } = useQuery(
    ['videos-all'],
    async () => {
      if (!projects) return {}
      const videosByProject: Record<number, Video[]> = {}
      await Promise.all(
        projects.map(async (project) => {
          if (project.project_type === 'template') {
            // For template projects, skip video fetch (they use generations)
            videosByProject[project.id] = []
          } else {
            const res = await videosApi.listByProject(project.id)
            videosByProject[project.id] = res.data.items
          }
        })
      )
      return videosByProject
    },
    { enabled: !!projects }
  )

  // Fetch generation counts for template projects
  const { data: templateGenerationCounts } = useQuery(
    ['template-generation-counts'],
    async () => {
      if (!projects) return {}
      const counts: Record<number, number> = {}
      const templateProjects = projects.filter(p => p.project_type === 'template')
      await Promise.all(
        templateProjects.map(async (project) => {
          try {
            const res = await templateApi.listGenerations(project.id, { offset: 0, limit: 1 }) // Fetch just 1 to get total
            counts[project.id] = res.data.total
          } catch {
            counts[project.id] = 0
          }
        })
      )
      return counts
    },
    { enabled: !!projects }
  )

  // Create project mutation
  const createMutation = useMutation(
    (data: CreateProjectDto) => projectsApi.create(data),
    {
      onSuccess: async (newProject) => {
        queryClient.invalidateQueries('projects')
        setSelectedProjectId(newProject.data.id)
      },
    }
  )

  // Collect all videos with filtering
  const filteredVideos = useMemo(() => {
    if (!allVideos) return []

    let videos: Video[] = selectedProjectId
      ? allVideos[selectedProjectId] || []
      : Object.values(allVideos).flat()

    switch (activeFilter) {
      case 'in_progress': return videos.filter(v => isInProgress(v.status || ''))
      case 'ready': return videos.filter(v => isReady(v))
      case 'published': return videos.filter(v => isPublished(v))
      case 'errors': return videos.filter(v => isError(v.status || ''))
      default: return videos
    }
  }, [allVideos, selectedProjectId, activeFilter])

  // Calculate counts for badges
  const counts = useMemo(() => {
    if (!allVideos) return { all: 0, in_progress: 0, ready: 0, published: 0, errors: 0 }

    const videos: Video[] = selectedProjectId
      ? allVideos[selectedProjectId] || []
      : Object.values(allVideos).flat()

    return {
      all: videos.length,
      in_progress: videos.filter(v => isInProgress(v.status || '')).length,
      ready: videos.filter(v => isReady(v)).length,
      published: videos.filter(v => isPublished(v)).length,
      errors: videos.filter(v => isError(v.status || '')).length
    }
  }, [allVideos, selectedProjectId])

  return {
    // State
    selectedProjectId,
    activeFilter,

    // Setters
    setSelectedProjectId,
    setActiveFilter,

    // Data
    projects,
    discoverProjects,
    workspaces,
    allVideos,
    templateGenerationCounts,
    filteredVideos,
    counts,

    // Loading states
    projectsLoading,

    // Mutations
    createProject: createMutation.mutate,
    isCreating: createMutation.isLoading,
  }
}
