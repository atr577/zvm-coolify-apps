import { useMemo, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useSearchParams } from 'react-router-dom'
import { projectsApi, videosApi, workspacesApi } from '@/services/api'
import type { Video, CreateProjectDto, Workspace } from '@/types'

export type FilterTab = 'all' | 'in_progress' | 'published' | 'errors'

const IN_PROGRESS_STATUSES = ['pending', 'in_progress', 'awaiting_approval', 'validating']
const ERROR_STATUSES = ['failed', 'validation_failed']

function isInProgress(status: string): boolean {
  return IN_PROGRESS_STATUSES.includes(status.toLowerCase())
}

function isError(status: string): boolean {
  return ERROR_STATUSES.includes(status.toLowerCase())
}

function isPublished(status: string): boolean {
  return status.toLowerCase() === 'completed'
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

  // Fetch videos for all projects
  const { data: allVideos } = useQuery(
    ['videos-all'],
    async () => {
      if (!projects) return {}
      const videosByProject: Record<number, Video[]> = {}
      await Promise.all(
        projects.map(async (project) => {
          const res = await videosApi.listByProject(project.id)
          videosByProject[project.id] = res.data.items
        })
      )
      return videosByProject
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

    const status = (v: Video) => v.status || ''
    switch (activeFilter) {
      case 'in_progress': return videos.filter(v => isInProgress(status(v)))
      case 'published': return videos.filter(v => isPublished(status(v)))
      case 'errors': return videos.filter(v => isError(status(v)))
      default: return videos
    }
  }, [allVideos, selectedProjectId, activeFilter])

  // Calculate counts for badges
  const counts = useMemo(() => {
    if (!allVideos) return { all: 0, in_progress: 0, published: 0, errors: 0 }

    const videos: Video[] = selectedProjectId
      ? allVideos[selectedProjectId] || []
      : Object.values(allVideos).flat()

    const status = (v: Video) => v.status || ''
    return {
      all: videos.length,
      in_progress: videos.filter(v => isInProgress(status(v))).length,
      published: videos.filter(v => isPublished(status(v))).length,
      errors: videos.filter(v => isError(status(v))).length
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
    workspaces,
    allVideos,
    filteredVideos,
    counts,

    // Loading states
    projectsLoading,

    // Mutations
    createProject: createMutation.mutate,
    isCreating: createMutation.isLoading,
  }
}
