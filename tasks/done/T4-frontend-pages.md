---
id: T4
title: "Frontend - Pages"
status: done
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: ['frontend']
depends_on: ['T03']
estimate: "3-4 часа"
branch: ""
---

# Task 04: Frontend - Pages

## Цель

Создать/переписать страницы для новой структуры.

## Подзадачи

### 4.1 Обновить API клиент

**Файл:** `frontend/src/services/api.ts`

```typescript
import axios from 'axios'
import type { Project, CreateProjectDto, Video, ContentVariant } from '@/types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Projects API
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects'),
  get: (id: number) => api.get<Project>(`/api/projects/${id}`),
  create: (data: CreateProjectDto) => api.post<Project>('/api/projects', data),
  update: (id: number, data: Partial<CreateProjectDto>) =>
    api.patch<Project>(`/api/projects/${id}`, data),
  delete: (id: number) => api.delete(`/api/projects/${id}`),
}

// Videos API
export const videosApi = {
  listByProject: (projectId: number) =>
    api.get<Video[]>(`/api/videos/project/${projectId}`),
  get: (id: number) => api.get<Video>(`/api/videos/${id}`),
  create: (data: { project_id: number; title: string; content_variables: any; is_template: boolean }) =>
    api.post<Video>('/api/videos', data),
  update: (id: number, data: Partial<Video>) =>
    api.patch<Video>(`/api/videos/${id}`, data),
  delete: (id: number) => api.delete(`/api/videos/${id}`),
}

// AI Generation API
export const aiApi = {
  generateVariants: (projectId: number) =>
    api.post<{ variants: ContentVariant[] }>('/api/ai/generate-variants', { project_id: projectId }),

  regenerateVariants: (projectId: number, exclude: ContentVariant[]) =>
    api.post<{ variants: ContentVariant[] }>('/api/ai/regenerate-variants', {
      project_id: projectId,
      exclude_variants: exclude
    }),
}

// Workflow API (обновленный)
export const workflowApi = {
  generateStory: (videoId: number, params: any) =>
    api.post('/api/workflow/generate-story', { video_id: videoId, ...params }),

  generateDescription: (videoId: number) =>
    api.post('/api/workflow/generate-description', { video_id: videoId }),

  generatePrompt: (videoId: number) =>
    api.post('/api/workflow/generate-prompt', { video_id: videoId }),

  generateImage: (videoId: number, prompt: string) =>
    api.post('/api/workflow/generate-image', { video_id: videoId, prompt }),

  generateScenario: (videoId: number) =>
    api.post('/api/workflow/generate-scenario', { video_id: videoId }),

  generateVideo: (videoId: number) =>
    api.post('/api/workflow/generate-video', { video_id: videoId }),

  adaptForPlatforms: (videoId: number, platforms: string[]) =>
    api.post('/api/workflow/adapt-for-platforms', { video_id: videoId, platforms }),

  approveStep: (stepId: number, approved: boolean, feedback?: string) =>
    api.post('/api/workflow/approve-step', { step_id: stepId, approved, feedback }),

  autoGenerateToVideo: (videoId: number) =>
    api.post('/api/workflow/auto-generate-to-video', { video_id: videoId }),
}

export default api
```

**Чеклист:**
- [ ] Обновить projectsApi
- [ ] Добавить videosApi
- [ ] Добавить aiApi
- [ ] Обновить workflowApi (video_id вместо project_id)

---

### 4.2 Dashboard - новая версия

**Файл:** `frontend/src/pages/Dashboard.tsx` (переписать)

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { projectsApi, videosApi } from '@/services/api'
import ProjectCard from '@/components/ProjectCard'
import ProjectForm from '@/components/ProjectForm'
import type { Project, Video, CreateProjectDto } from '@/types'

export default function Dashboard() {
  const [isCreating, setIsCreating] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Получить все проекты
  const { data: projects, isLoading: projectsLoading } = useQuery(
    'projects',
    () => projectsApi.list().then(res => res.data)
  )

  // Получить видео для всех проектов
  const { data: allVideos } = useQuery(
    ['videos-all'],
    async () => {
      if (!projects) return {}
      const videosByProject: Record<number, Video[]> = {}

      await Promise.all(
        projects.map(async (project) => {
          const videos = await videosApi.listByProject(project.id).then(res => res.data)
          videosByProject[project.id] = videos
        })
      )

      return videosByProject
    },
    { enabled: !!projects }
  )

  // Создание проекта
  const createMutation = useMutation(
    (data: CreateProjectDto) => projectsApi.create(data),
    {
      onSuccess: async (newProject) => {
        queryClient.invalidateQueries('projects')
        setIsCreating(false)

        // Редирект на создание первого ролика
        navigate(`/project/${newProject.data.id}/create-video`)
      },
    }
  )

  if (projectsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Проекты</h1>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          <Plus className="h-5 w-5 mr-2" />
          Создать проект
        </button>
      </div>

      {/* Форма создания проекта */}
      {isCreating && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-semibold mb-4">Создать новый проект</h2>
          <ProjectForm
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setIsCreating(false)}
            isLoading={createMutation.isLoading}
          />
        </div>
      )}

      {/* Список проектов */}
      <div className="space-y-4">
        {projects?.map((project: Project) => (
          <ProjectCard
            key={project.id}
            project={project}
            videos={allVideos?.[project.id] || []}
            onCreateVideo={(projectId) => navigate(`/project/${projectId}/create-video`)}
            onEditProject={(projectId) => navigate(`/project/${projectId}/edit`)}
            onVideoClick={(videoId) => navigate(`/video/${videoId}`)}
          />
        ))}
      </div>

      {projects?.length === 0 && !isCreating && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">Нет проектов. Создайте первый!</p>
        </div>
      )}
    </div>
  )
}
```

**Чеклист:**
- [ ] Переписать Dashboard
- [ ] Список проектов с раскрываемыми карточками
- [ ] Форма создания проекта
- [ ] После создания проекта → редирект на создание первого ролика
- [ ] Удалить старую логику

---

### 4.3 ProjectEdit - редактирование шаблона проекта

**Файл:** `frontend/src/pages/ProjectEdit.tsx` (новый)

```tsx
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { ArrowLeft } from 'lucide-react'
import { projectsApi } from '@/services/api'
import ProjectForm from '@/components/ProjectForm'
import type { CreateProjectDto } from '@/types'

export default function ProjectEdit() {
  const { id } = useParams<{ id: string }>()
  const projectId = parseInt(id || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: project, isLoading } = useQuery(
    ['project', projectId],
    () => projectsApi.get(projectId).then(res => res.data)
  )

  const updateMutation = useMutation(
    (data: CreateProjectDto) => projectsApi.update(projectId, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['project', projectId])
        queryClient.invalidateQueries('projects')
        navigate('/')
      },
    }
  )

  if (isLoading || !project) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5 mr-2" />
          Назад к проектам
        </button>

        <h1 className="text-3xl font-bold text-gray-900">
          Редактирование проекта: {project.name}
        </h1>
      </div>

      {/* Form */}
      <div className="bg-white p-6 rounded-lg shadow">
        <ProjectForm
          initialData={project}
          onSubmit={(data) => updateMutation.mutate(data)}
          onCancel={() => navigate('/')}
          isLoading={updateMutation.isLoading}
        />
      </div>
    </div>
  )
}
```

**Чеклист:**
- [ ] Создать страницу ProjectEdit
- [ ] Загрузка данных проекта
- [ ] Форма редактирования
- [ ] Сохранение изменений
- [ ] Кнопка "Назад"

---

### 4.4 CreateVideo - выбор варианта контента

**Файл:** `frontend/src/pages/CreateVideo.tsx` (новый)

```tsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { ArrowLeft } from 'lucide-react'
import { projectsApi, aiApi, videosApi } from '@/services/api'
import VideoVariantSelector from '@/components/VideoVariantSelector'
import type { ContentVariant } from '@/types'

export default function CreateVideo() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = parseInt(projectId || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [variants, setVariants] = useState<ContentVariant[]>([])
  const [excludedVariants, setExcludedVariants] = useState<ContentVariant[]>([])

  const { data: project } = useQuery(
    ['project', id],
    () => projectsApi.get(id).then(res => res.data)
  )

  // Проверить есть ли уже template video в проекте
  const { data: existingVideos } = useQuery(
    ['videos', id],
    () => videosApi.listByProject(id).then(res => res.data)
  )

  const isFirstVideo = !existingVideos || existingVideos.length === 0
  const hasTemplateVideo = existingVideos?.some(v => v.is_template)

  // Генерация вариантов
  const generateMutation = useMutation(
    () => aiApi.generateVariants(id),
    {
      onSuccess: (data) => {
        setVariants(data.data.variants)
      },
    }
  )

  const regenerateMutation = useMutation(
    () => aiApi.regenerateVariants(id, excludedVariants),
    {
      onSuccess: (data) => {
        setExcludedVariants([...excludedVariants, ...variants])
        setVariants(data.data.variants)
      },
    }
  )

  // Создание видео
  const createVideoMutation = useMutation(
    (variant: ContentVariant) => {
      const title = variant.description
      const isTemplate = isFirstVideo // Первое видео = template

      return videosApi.create({
        project_id: id,
        title,
        content_variables: variant.content_variables,
        is_template: isTemplate
      })
    },
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['videos', id])
        navigate(`/video/${data.data.id}`)
      },
    }
  )

  // Генерируем варианты при загрузке
  useEffect(() => {
    generateMutation.mutate()
  }, [])

  if (!project) {
    return <div>Loading...</div>
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5 mr-2" />
          Назад
        </button>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Создание ролика в проекте: {project.name}
        </h1>

        {isFirstVideo && (
          <p className="text-sm text-blue-600">
            ℹ️ Это будет шаблонный ролик (Template Video) с полным контролем всех этапов
          </p>
        )}

        {!isFirstVideo && !hasTemplateVideo && (
          <p className="text-sm text-yellow-600">
            ⚠️ В проекте еще нет шаблонного ролика. Этот ролик будет помечен как template.
          </p>
        )}
      </div>

      {/* Генерация вариантов */}
      {generateMutation.isLoading && (
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-600">AI анализирует шаблон и генерирует вариации...</p>
          </div>
        </div>
      )}

      {/* Выбор варианта */}
      {!generateMutation.isLoading && variants.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <VideoVariantSelector
            variants={variants}
            onSelect={(variant) => createVideoMutation.mutate(variant)}
            onRegenerate={() => regenerateMutation.mutate()}
            isRegenerating={regenerateMutation.isLoading}
          />
        </div>
      )}

      {/* Ошибка */}
      {generateMutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Ошибка при генерации вариантов. Попробуйте еще раз.
        </div>
      )}
    </div>
  )
}
```

**Чеклист:**
- [ ] Создать страницу CreateVideo
- [ ] Генерация 10 вариантов при загрузке
- [ ] Использовать VideoVariantSelector
- [ ] Определять is_template (первый ролик = true)
- [ ] После выбора → создать Video → редирект на VideoDetail

---

### 4.5 VideoDetail - просмотр/редактирование ролика

**Файл:** `frontend/src/pages/VideoDetail.tsx` (новый)

```tsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { ArrowLeft, Settings, Trash2 } from 'lucide-react'
import { videosApi, workflowApi } from '@/services/api'
import VideoWorkflowView from '@/components/VideoWorkflowView'
import type { Video } from '@/types'

export default function VideoDetail() {
  const { id } = useParams<{ id: string }>()
  const videoId = parseInt(id || '0')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [feedback, setFeedback] = useState('')

  const { data: video, isLoading } = useQuery(
    ['video', videoId],
    () => videosApi.get(videoId).then(res => res.data),
    { refetchInterval: 5000 }
  )

  // Approve step
  const approveMutation = useMutation(
    ({ stepId, approved }: { stepId: number; approved: boolean }) =>
      workflowApi.approveStep(stepId, approved, feedback),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['video', videoId])
        setFeedback('')
      },
    }
  )

  // Delete video
  const deleteMutation = useMutation(
    () => videosApi.delete(videoId),
    {
      onSuccess: () => {
        navigate('/')
      },
    }
  )

  // Toggle template flag
  const toggleTemplateMutation = useMutation(
    () => videosApi.update(videoId, { is_template: !video?.is_template }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['video', videoId])
      },
    }
  )

  if (isLoading || !video) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <button
            onClick={() => navigate('/')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Назад к проектам
          </button>

          <div className="flex items-center space-x-3">
            <h1 className="text-3xl font-bold text-gray-900">{video.title}</h1>
            {video.is_template && (
              <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded">
                Template Video
              </span>
            )}
          </div>

          <p className="text-gray-600 mt-2">
            Проект ID: {video.project_id} •
            Статус: <span className="capitalize">{video.status.replace('_', ' ')}</span>
          </p>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={() => toggleTemplateMutation.mutate()}
            className="flex items-center px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md transition"
          >
            <Settings className="h-4 w-4 mr-2" />
            {video.is_template ? 'Убрать Template' : 'Сделать Template'}
          </button>

          <button
            onClick={() => {
              if (confirm('Удалить ролик?')) {
                deleteMutation.mutate()
              }
            }}
            className="flex items-center px-3 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Удалить
          </button>
        </div>
      </div>

      {/* Content Variables */}
      {video.content_variables && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h3 className="text-lg font-semibold mb-3">Параметры контента</h3>
          <pre className="text-sm bg-gray-50 p-4 rounded overflow-x-auto">
            {JSON.stringify(video.content_variables, null, 2)}
          </pre>
        </div>
      )}

      {/* Workflow Steps */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Этапы генерации</h3>
        <VideoWorkflowView steps={video.workflow_steps || []} />
      </div>

      {/* TODO: Добавить блок approve/reject для финального видео */}
      {/* TODO: Добавить автогенерацию для обычных роликов */}
    </div>
  )
}
```

**Чеклист:**
- [ ] Создать страницу VideoDetail
- [ ] Показать название, статус, is_template badge
- [ ] Показать content_variables
- [ ] Использовать VideoWorkflowView для этапов
- [ ] Кнопка toggle template flag
- [ ] Кнопка удаления
- [ ] TODO: Логика approve/reject и автогенерации

---

### 4.6 Обновить роутинг

**Файл:** `frontend/src/App.tsx`

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import Dashboard from './pages/Dashboard'
import ProjectEdit from './pages/ProjectEdit'
import CreateVideo from './pages/CreateVideo'
import VideoDetail from './pages/VideoDetail'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/project/:id/edit" element={<ProjectEdit />} />
              <Route path="/project/:projectId/create-video" element={<CreateVideo />} />
              <Route path="/video/:id" element={<VideoDetail />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
```

**Чеклист:**
- [ ] Добавить роуты для новых страниц
- [ ] Удалить старые неиспользуемые роуты

---

## Проверка результата

**Тестирование flow:**

1. **Создание проекта:**
   - [ ] Dashboard → Создать проект
   - [ ] Заполнить форму
   - [ ] После создания редирект на CreateVideo

2. **Создание первого ролика (Template):**
   - [ ] AI генерирует 10 вариантов
   - [ ] Выбрать вариант
   - [ ] Создается Video с is_template=true
   - [ ] Редирект на VideoDetail

3. **Просмотр ролика:**
   - [ ] Видны все workflow steps
   - [ ] Можно раскрыть и посмотреть детали
   - [ ] Badge "Template Video"

4. **Создание второго ролика:**
   - [ ] Dashboard → раскрыть проект → Создать новый ролик
   - [ ] AI генерирует новые 10 вариантов
   - [ ] Выбрать → создается с is_template=false

5. **Редактирование проекта:**
   - [ ] Dashboard → ⚙️ Настройки
   - [ ] Изменить Story Template
   - [ ] Сохранить

**Критерии приемки:**
- [ ] Все страницы работают без ошибок
- [ ] Навигация между страницами корректная
- [ ] Данные отображаются правильно
- [ ] API запросы выполняются успешно

---

**Статус:** ✅ Завершено

**Выполнено:**
- ✅ Обновлен API клиент (projectsApi, videosApi, aiApi, workflowApi с video_id)
- ✅ Переписана страница Dashboard (раскрываемые проекты, список роликов)
- ✅ Создана страница ProjectEdit (редактирование шаблона проекта)
- ✅ Создана страница CreateVideo (генерация AI вариантов и выбор)
- ✅ Создана страница VideoDetail (просмотр workflow steps, video preview)
- ✅ Обновлен роутинг в App.tsx

**Созданные файлы:**
- `frontend/src/services/api.ts` - обновлен
- `frontend/src/pages/Dashboard.tsx` - переписан
- `frontend/src/pages/ProjectEdit.tsx` - создан
- `frontend/src/pages/CreateVideo.tsx` - создан
- `frontend/src/pages/VideoDetail.tsx` - создан
- `frontend/src/App.tsx` - обновлен

**TODO для будущей итерации:**
- [ ] Добавить approve/reject логику в VideoDetail
- [ ] Добавить кнопку автогенерации для обычных роликов
- [ ] Реализовать real-time обновления через WebSocket
- [ ] Добавить индикаторы прогресса генерации

**Ответственный:** Frontend Developer
