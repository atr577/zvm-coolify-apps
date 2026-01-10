---
id: T3
title: "Frontend - Components"
status: done
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: ['frontend', 'backend']
depends_on: ['T02']
estimate: "4-5 часов"
branch: ""
---

# Task 03: Frontend - Components

## Цель

Создать React компоненты для новой структуры (проекты + видео).

## Подзадачи

### 3.1 Обновить типы TypeScript

**Файл:** `frontend/src/types/index.ts`

```typescript
export interface Project {
  id: number
  name: string
  description?: string
  story_template: string
  platforms: string[]
  duration: number
  created_at: string
  updated_at: string
}

export interface CreateProjectDto {
  name: string
  description?: string
  story_template: string
  platforms: string[]
  duration: number
}

export interface Video {
  id: number
  project_id: number
  title: string
  is_template: boolean
  template_video_id?: number
  content_variables?: Record<string, any>

  story_data?: any
  description_data?: any
  image_prompt?: string
  image_url?: string
  scenario_data?: any
  video_url?: string
  adaptation_data?: any

  current_step: string
  status: string

  created_at: string
  updated_at: string
}

export interface ContentVariant {
  id: number
  description: string
  content_variables: {
    character?: Record<string, any>
    vehicle?: Record<string, any>
    location?: Record<string, any>
  }
}

export interface WorkflowStep {
  id: number
  video_id: number
  step_type: string
  status: string
  content?: any
  user_approved?: boolean
  user_feedback?: string
  prompt_used?: string
  generation_time_seconds?: number
  started_at?: string
  completed_at?: string
  created_at: string
}
```

**Чеклист:**
- [ ] Создать/обновить типы Project, Video
- [ ] Добавить ContentVariant
- [ ] Обновить WorkflowStep (video_id вместо project_id)
- [ ] Удалить старые неиспользуемые типы

---

### 3.2 ProjectCard - раскрываемая карточка проекта

**Файл:** `frontend/src/components/ProjectCard.tsx` (новый)

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight, Settings, Plus } from 'lucide-react'
import { Project, Video } from '@/types'
import VideoCard from './VideoCard'

interface ProjectCardProps {
  project: Project
  videos: Video[]
  onCreateVideo: (projectId: number) => void
  onEditProject: (projectId: number) => void
  onVideoClick: (videoId: number) => void
}

export default function ProjectCard({
  project,
  videos,
  onCreateVideo,
  onEditProject,
  onVideoClick
}: ProjectCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const publishedCount = videos.filter(v => v.status === 'completed').length
  const latestVideos = videos.slice(0, 3)

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition">
      {/* Header - клик раскрывает */}
      <div
        className="p-6 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <button className="mt-1">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronRight className="h-5 w-5 text-gray-500" />
              )}
            </button>

            <div className="flex-1">
              <h3 className="text-xl font-semibold text-gray-900 mb-1">
                📁 {project.name}
              </h3>
              {project.description && (
                <p className="text-sm text-gray-600 mb-2">{project.description}</p>
              )}

              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>{videos.length} роликов</span>
                <span>•</span>
                <span>{publishedCount} опубликовано</span>
              </div>
            </div>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation()
              onEditProject(project.id)
            }}
            className="text-gray-400 hover:text-primary-600 transition"
          >
            <Settings className="h-5 w-5" />
          </button>
        </div>

        {/* Preview последних роликов (если не раскрыто) */}
        {!isExpanded && videos.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-gray-500 uppercase">Последние:</p>
            {latestVideos.map(video => (
              <div key={video.id} className="text-sm text-gray-700">
                • {video.title} - {getStatusLabel(video.status)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Expanded content - список всех роликов */}
      {isExpanded && (
        <div className="px-6 pb-6 border-t">
          <div className="mt-4 space-y-3">
            {videos.map(video => (
              <VideoCard
                key={video.id}
                video={video}
                onClick={() => onVideoClick(video.id)}
              />
            ))}

            {videos.length === 0 && (
              <p className="text-center text-gray-500 py-8">
                Нет роликов в этом проекте
              </p>
            )}
          </div>

          <button
            onClick={() => onCreateVideo(project.id)}
            className="mt-4 w-full flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
          >
            <Plus className="h-5 w-5 mr-2" />
            Создать новый ролик
          </button>
        </div>
      )}
    </div>
  )
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '📝 Черновик',
    in_progress: '🔄 Генерация',
    completed: '✅ Опубликован',
    failed: '❌ Ошибка'
  }
  return map[status] || status
}
```

**Чеклист:**
- [ ] Создать компонент ProjectCard
- [ ] Раскрываемая логика (useState)
- [ ] Preview последних роликов
- [ ] Кнопка создания ролика
- [ ] Кнопка настроек проекта

---

### 3.3 VideoCard - карточка ролика

**Файл:** `frontend/src/components/VideoCard.tsx` (новый)

```tsx
import { Video } from '@/types'
import { Clock, CheckCircle, XCircle, Film } from 'lucide-react'

interface VideoCardProps {
  video: Video
  onClick: () => void
}

export default function VideoCard({ video, onClick }: VideoCardProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />
    }
  }

  const getStepLabel = (step: string) => {
    const map: Record<string, string> = {
      story: 'Story',
      description: 'Description',
      prompt: 'Prompt',
      image: 'Image',
      scenario: 'Scenario',
      video: 'Video',
      adaptation: 'Adaptation',
      publishing: 'Publishing'
    }
    return map[step] || step
  }

  return (
    <div
      onClick={onClick}
      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition"
    >
      <div className="flex items-center space-x-3 flex-1">
        <Film className="h-5 w-5 text-primary-600" />

        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium text-gray-900">{video.title}</h4>
            {video.is_template && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                Template
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500">
            <span>Step: {getStepLabel(video.current_step)}</span>
            <span>•</span>
            <span>{new Date(video.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {getStatusIcon(video.status)}
        <span className="text-sm text-gray-600 capitalize">
          {video.status.replace('_', ' ')}
        </span>
      </div>
    </div>
  )
}
```

**Чеклист:**
- [ ] Создать компонент VideoCard
- [ ] Показать название, статус, current_step
- [ ] Badge для template video
- [ ] Иконки статусов

---

### 3.4 ProjectForm - форма создания/редактирования проекта

**Файл:** `frontend/src/components/ProjectForm.tsx` (новый)

```tsx
import { useState } from 'react'
import { CreateProjectDto } from '@/types'

interface ProjectFormProps {
  initialData?: Partial<CreateProjectDto>
  onSubmit: (data: CreateProjectDto) => void
  onCancel: () => void
  isLoading: boolean
}

export default function ProjectForm({
  initialData,
  onSubmit,
  onCancel,
  isLoading
}: ProjectFormProps) {
  const [formData, setFormData] = useState<CreateProjectDto>({
    name: initialData?.name || '',
    description: initialData?.description || '',
    story_template: initialData?.story_template || '',
    platforms: initialData?.platforms || [],
    duration: initialData?.duration || 5
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const togglePlatform = (platform: string) => {
    setFormData(prev => ({
      ...prev,
      platforms: prev.platforms.includes(platform)
        ? prev.platforms.filter(p => p !== platform)
        : [...prev.platforms, platform]
    }))
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Название */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Название проекта *
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Девушки и авто"
          required
        />
      </div>

      {/* Описание */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Описание (опционально)
        </label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          rows={2}
          placeholder="Роскошные девушки у премиум авто в мировых столицах"
        />
      </div>

      {/* Platforms */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Platforms *
        </label>
        <div className="flex space-x-4">
          {['instagram', 'tiktok', 'youtube'].map(platform => (
            <label key={platform} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.platforms.includes(platform)}
                onChange={() => togglePlatform(platform)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="capitalize">{platform}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Duration */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Duration *
        </label>
        <div className="flex space-x-4">
          {[5, 10, 15].map(duration => (
            <label key={duration} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="duration"
                checked={formData.duration === duration}
                onChange={() => setFormData({ ...formData, duration })}
                className="border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span>{duration} сек</span>
            </label>
          ))}
        </div>
      </div>

      {/* Story Template */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Story Template (концепция ролика) *
        </label>
        <textarea
          value={formData.story_template}
          onChange={(e) => setFormData({ ...formData, story_template: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          rows={6}
          placeholder="Элегантная девушка в стильном наряде выходит из роскошного автомобиля премиум класса на фоне узнаваемой локации мирового города..."
          required
        />
      </div>

      {/* Buttons */}
      <div className="flex space-x-3">
        <button
          type="submit"
          disabled={isLoading || !formData.name || !formData.story_template || formData.platforms.length === 0}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Сохранение...' : 'Создать проект'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
        >
          Отмена
        </button>
      </div>
    </form>
  )
}
```

**Чеклист:**
- [ ] Создать компонент ProjectForm
- [ ] Поля: name, description, story_template, platforms, duration
- [ ] Валидация (required поля)
- [ ] Обработка submit

---

### 3.5 VideoVariantSelector - выбор из 10 вариантов

**Файл:** `frontend/src/components/VideoVariantSelector.tsx` (новый)

```tsx
import { useState } from 'react'
import { ContentVariant } from '@/types'
import { RefreshCw } from 'lucide-react'

interface VideoVariantSelectorProps {
  variants: ContentVariant[]
  onSelect: (variant: ContentVariant) => void
  onRegenerate: () => void
  isRegenerating: boolean
}

export default function VideoVariantSelector({
  variants,
  onSelect,
  onRegenerate,
  isRegenerating
}: VideoVariantSelectorProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Выберите вариант контента</h3>
        <button
          onClick={onRegenerate}
          disabled={isRegenerating}
          className="flex items-center space-x-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${isRegenerating ? 'animate-spin' : ''}`} />
          <span>Другие варианты</span>
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 max-h-[500px] overflow-y-auto">
        {variants.map((variant) => (
          <label
            key={variant.id}
            className={`
              flex items-start space-x-3 p-4 border-2 rounded-lg cursor-pointer transition
              ${selectedId === variant.id
                ? 'border-primary-600 bg-primary-50'
                : 'border-gray-200 hover:border-primary-300'
              }
            `}
          >
            <input
              type="radio"
              name="variant"
              checked={selectedId === variant.id}
              onChange={() => setSelectedId(variant.id)}
              className="mt-1"
            />
            <div className="flex-1">
              <p className="text-gray-900 font-medium">{variant.description}</p>

              {/* Детали */}
              <div className="mt-2 text-sm text-gray-600 space-y-1">
                {variant.content_variables.character && (
                  <div>
                    <span className="font-semibold">Персонаж:</span>{' '}
                    {JSON.stringify(variant.content_variables.character)}
                  </div>
                )}
                {variant.content_variables.vehicle && (
                  <div>
                    <span className="font-semibold">Авто:</span>{' '}
                    {JSON.stringify(variant.content_variables.vehicle)}
                  </div>
                )}
                {variant.content_variables.location && (
                  <div>
                    <span className="font-semibold">Локация:</span>{' '}
                    {JSON.stringify(variant.content_variables.location)}
                  </div>
                )}
              </div>
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={() => {
          const selected = variants.find(v => v.id === selectedId)
          if (selected) onSelect(selected)
        }}
        disabled={!selectedId}
        className="w-full px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Выбрать
      </button>
    </div>
  )
}
```

**Чеклист:**
- [ ] Создать компонент VideoVariantSelector
- [ ] Radio buttons для выбора варианта
- [ ] Кнопка "Другие варианты"
- [ ] Показ деталей каждого варианта
- [ ] Кнопка "Выбрать"

---

### 3.6 VideoWorkflowView - просмотр этапов с деталями

**Файл:** `frontend/src/components/VideoWorkflowView.tsx` (новый)

```tsx
import { useState } from 'react'
import { WorkflowStep } from '@/types'
import { ChevronDown, ChevronRight, CheckCircle, Clock, XCircle } from 'lucide-react'

interface VideoWorkflowViewProps {
  steps: WorkflowStep[]
}

export default function VideoWorkflowView({ steps }: VideoWorkflowViewProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({})

  const toggleStep = (stepId: number) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepId]: !prev[stepId]
    }))
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
      case 'rejected':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'in_progress':
        return <Clock className="h-5 w-5 text-yellow-500 animate-pulse" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  const getStepLabel = (stepType: string) => {
    const map: Record<string, string> = {
      story: 'Story',
      description: 'Description',
      prompt: 'Prompt',
      image: 'Image',
      scenario: 'Scenario',
      video: 'Video',
      adaptation: 'Adaptation',
      publishing: 'Publishing'
    }
    return map[stepType] || stepType
  }

  return (
    <div className="space-y-2">
      {steps.map((step, index) => {
        const isExpanded = expandedSteps[step.id] || false

        return (
          <div key={step.id} className="bg-white border rounded-lg">
            {/* Header */}
            <div
              onClick={() => toggleStep(step.id)}
              className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
            >
              <div className="flex items-center space-x-3 flex-1">
                <button>
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-500" />
                  )}
                </button>

                <span className="text-sm font-medium text-gray-500">
                  Step {index + 1}:
                </span>

                <h4 className="font-semibold text-gray-900">
                  {getStepLabel(step.step_type)}
                </h4>

                {getStatusIcon(step.status)}

                <span className="text-sm text-gray-600 capitalize">
                  {step.status.replace('_', ' ')}
                </span>
              </div>

              {step.generation_time_seconds && (
                <span className="text-xs text-gray-500">
                  {step.generation_time_seconds.toFixed(1)}s
                </span>
              )}
            </div>

            {/* Expanded content */}
            {isExpanded && (
              <div className="px-4 pb-4 border-t space-y-3">
                {/* Prompt used */}
                {step.prompt_used && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Промпт:
                    </h5>
                    <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                      {step.prompt_used}
                    </pre>
                  </div>
                )}

                {/* Content result */}
                {step.content && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Результат:
                    </h5>
                    <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto max-h-64">
                      {JSON.stringify(step.content, null, 2)}
                    </pre>
                  </div>
                )}

                {/* User feedback */}
                {step.user_feedback && (
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Фидбек пользователя:
                    </h5>
                    <p className="text-sm text-gray-600">{step.user_feedback}</p>
                  </div>
                )}

                {/* Timestamps */}
                <div className="flex space-x-4 text-xs text-gray-500">
                  {step.started_at && (
                    <span>Начало: {new Date(step.started_at).toLocaleString()}</span>
                  )}
                  {step.completed_at && (
                    <span>Завершено: {new Date(step.completed_at).toLocaleString()}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

**Чеклист:**
- [ ] Создать компонент VideoWorkflowView
- [ ] Раскрываемые этапы
- [ ] Показ промпта, результата, времени генерации
- [ ] Иконки статусов
- [ ] User feedback если есть

---

## Проверка результата

**Критерии приемки:**
- [ ] Все компоненты отрисовываются без ошибок
- [ ] ProjectCard раскрывается/сворачивается
- [ ] VideoVariantSelector позволяет выбрать вариант
- [ ] VideoWorkflowView показывает детали этапов
- [ ] Типы TypeScript корректны

---

**Статус:** ✅ Завершено

**Выполнено:**
- ✅ Обновлены TypeScript типы (Project, Video, ContentVariant, WorkflowStep с video_id)
- ✅ Создан компонент ProjectCard (раскрываемая карточка проекта)
- ✅ Создан компонент VideoCard (карточка ролика)
- ✅ Создан компонент ProjectForm (форма создания/редактирования проекта)
- ✅ Создан компонент VideoVariantSelector (выбор из 10 вариантов AI)
- ✅ Создан компонент VideoWorkflowView (просмотр этапов с деталями)

**Компоненты готовы к использованию:**
- `frontend/src/types/index.ts` - обновлены типы
- `frontend/src/components/VideoCard.tsx`
- `frontend/src/components/ProjectCard.tsx`
- `frontend/src/components/ProjectForm.tsx`
- `frontend/src/components/VideoVariantSelector.tsx`
- `frontend/src/components/VideoWorkflowView.tsx`

**Ответственный:** Frontend Developer
