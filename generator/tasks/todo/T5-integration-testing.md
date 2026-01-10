---
id: T5
title: "Integration & Testing"
status: todo
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: ['backend', 'testing']
depends_on: ['T01']
estimate: "2-3 часа"
branch: ""
---

# Task 05: Integration & Testing

## Цель

Интегрировать все части системы и протестировать полный flow.

## Подзадачи

### 5.1 Реализовать автогенерацию для обычных роликов

**Файл:** `backend/app/api/workflow.py`

Добавить endpoint для автоматической генерации всех этапов до видео:

```python
@router.post("/auto-generate-to-video")
async def auto_generate_to_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Автоматическая генерация Steps 1-6 для обычных роликов
    Без checkpoints, последовательно
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    project = video.project
    start_time = datetime.utcnow()

    try:
        # Step 1: Story
        story_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(story_step)
        db.commit()

        story_data = await openai_service.generate_story_from_template(
            story_template=project.story_template,
            content_variables=video.content_variables,
            duration=project.duration,
            platforms=project.platforms
        )

        story_step.content = story_data
        story_step.status = WorkflowStatus.APPROVED
        story_step.completed_at = datetime.utcnow()
        story_step.generation_time_seconds = (datetime.utcnow() - story_step.started_at).total_seconds()

        video.story_data = story_data
        video.current_step = StepType.DESCRIPTION
        db.commit()

        # Step 2: Description
        desc_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.DESCRIPTION,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(desc_step)
        db.commit()

        description_data = await openai_service.generate_description(story_data)
        desc_step.content = description_data
        desc_step.status = WorkflowStatus.APPROVED
        desc_step.completed_at = datetime.utcnow()
        desc_step.generation_time_seconds = (datetime.utcnow() - desc_step.started_at).total_seconds()

        video.description_data = description_data
        video.current_step = StepType.PROMPT
        db.commit()

        # Step 3: Prompt
        # Step 4: Image
        # Step 5: Scenario
        # Step 6: Video
        # ... аналогично для остальных этапов

        # После генерации видео - останавливаемся
        video.current_step = StepType.VIDEO
        video.status = WorkflowStatus.AWAITING_APPROVAL
        db.commit()

        return {
            "video_id": video.id,
            "message": "Video generated successfully",
            "total_time_seconds": (datetime.utcnow() - start_time).total_seconds()
        }

    except Exception as e:
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

**Чеклист:**
- [ ] Реализовать auto-generate-to-video endpoint
- [ ] Последовательная генерация всех этапов
- [ ] Сохранение prompt_used и generation_time
- [ ] Остановка на Step 6 (Video)
- [ ] Error handling

---

### 5.2 Интегрировать автогенерацию во фронтенд

**Файл:** `frontend/src/pages/VideoDetail.tsx`

Добавить логику автозапуска для обычных роликов:

```tsx
// В VideoDetail.tsx

useEffect(() => {
  if (!video) return

  // Если это обычный ролик (не template) и он только создан
  if (!video.is_template && video.status === 'pending' && !video.story_data) {
    // Запускаем автогенерацию
    autoGenerateMutation.mutate()
  }
}, [video])

const autoGenerateMutation = useMutation(
  () => workflowApi.autoGenerateToVideo(videoId),
  {
    onSuccess: () => {
      queryClient.invalidateQueries(['video', videoId])
    },
    onError: (error) => {
      console.error('Auto-generation failed:', error)
    }
  }
)

// UI для показа прогресса автогенерации
{autoGenerateMutation.isLoading && (
  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
    <div className="flex items-center space-x-3 mb-4">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <div>
        <h3 className="font-semibold text-blue-900">Автоматическая генерация ролика...</h3>
        <p className="text-sm text-blue-700">
          Это может занять несколько минут. Вы можете закрыть страницу и вернуться позже.
        </p>
      </div>
    </div>
  </div>
)}

// UI для approve/reject финального видео
{video.video_url && video.status === 'awaiting_approval' && (
  <div className="bg-white p-6 rounded-lg shadow mb-6">
    <h3 className="text-lg font-semibold mb-4">Финальное видео готово!</h3>

    {/* Превью видео */}
    <video
      src={video.video_url}
      controls
      className="w-full max-h-[500px] rounded-lg mb-4"
    />

    {/* Feedback */}
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Комментарий (опционально):
      </label>
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md"
        rows={3}
        placeholder="Что нужно изменить?"
      />
    </div>

    {/* Actions */}
    <div className="flex space-x-3">
      <button
        onClick={() => handleApproveVideo()}
        className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
      >
        ✓ Approve
      </button>

      <button
        onClick={() => handleQuickRegenerate()}
        className="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
      >
        🔄 Regenerate
      </button>

      <button
        onClick={() => handleManualEdit()}
        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        ✏️ Manual Edit
      </button>

      <button
        onClick={() => handleDeleteVideo()}
        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
      >
        🗑️ Delete
      </button>
    </div>
  </div>
)}
```

**Чеклист:**
- [ ] Добавить useEffect для автозапуска
- [ ] UI для показа прогресса генерации
- [ ] UI для approve/reject финального видео
- [ ] Обработка 3 сценариев: Approve, Quick Regenerate, Manual Edit

---

### 5.3 Реализовать логику Approve → Adaptation → Publishing

**Backend:** После approve видео → автоматически Step 7 → Step 8

```python
# В workflow.py approve_step endpoint

if request.approved and step.step_type == StepType.VIDEO:
    # Автоматически запускаем адаптацию
    video = step.video
    project = video.project

    # Step 7: Adaptation
    adaptation_step = WorkflowStep(
        video_id=video.id,
        step_type=StepType.ADAPTATION,
        status=WorkflowStatus.IN_PROGRESS,
        started_at=datetime.utcnow()
    )
    db.add(adaptation_step)
    db.commit()

    adaptation_data = await openai_service.adapt_for_platforms(
        video.scenario_data,
        project.platforms
    )

    adaptation_step.content = adaptation_data
    adaptation_step.status = WorkflowStatus.APPROVED
    adaptation_step.completed_at = datetime.utcnow()

    video.adaptation_data = adaptation_data
    video.current_step = StepType.PUBLISHING
    video.status = WorkflowStatus.COMPLETED

    db.commit()
```

**Чеклист:**
- [ ] После approve Video → автоматом Adaptation
- [ ] После Adaptation → current_step = PUBLISHING
- [ ] Status = COMPLETED

---

### 5.4 Тестирование полного flow

#### Test Case 1: Создание проекта и первого template video

**Шаги:**
1. Dashboard → Создать проект
2. Заполнить:
   - Name: "Test Project"
   - Story Template: "Girl exits luxury car"
   - Platforms: Instagram, TikTok
   - Duration: 5 sec
3. Создать → редирект на CreateVideo
4. Дождаться генерации 10 вариантов
5. Выбрать вариант 1
6. Редирект на VideoDetail
7. Пройти все 8 этапов с approve на каждом

**Ожидаемый результат:**
- [ ] Проект создан
- [ ] Video создан с is_template=true
- [ ] Все 8 этапов выполнены
- [ ] Каждый этап имеет WorkflowStep с данными
- [ ] Видны промпты и результаты

---

#### Test Case 2: Создание второго обычного ролика

**Шаги:**
1. Dashboard → раскрыть проект → Создать новый ролик
2. Дождаться генерации 10 вариантов
3. Выбрать вариант 3
4. Редирект на VideoDetail
5. Автоматически запускается генерация
6. Дождаться генерации до Step 6 (Video)
7. Появляется approve/reject блок

**Ожидаемый результат:**
- [ ] Video создан с is_template=false
- [ ] Автогенерация запустилась
- [ ] Steps 1-6 выполнены без checkpoints
- [ ] Видео готово для ревью
- [ ] Можно approve/reject/regenerate/edit

---

#### Test Case 3: Approve обычного ролика

**Шаги:**
1. На VideoDetail обычного ролика (из Test Case 2)
2. Нажать Approve
3. Дождаться завершения

**Ожидаемый результат:**
- [ ] Step 7 (Adaptation) выполнен автоматически
- [ ] current_step = PUBLISHING
- [ ] status = COMPLETED
- [ ] Adaptation data сохранены

---

#### Test Case 4: Reject → Manual Edit

**Шаги:**
1. Создать обычный ролик (автогенерация до видео)
2. Нажать Manual Edit
3. Открывается полный workflow
4. Изменить промпт на шаге 3
5. Регенерировать шаги 3-6

**Ожидаемый результат:**
- [ ] Все этапы становятся редактируемыми
- [ ] Можно изменить промпты
- [ ] Можно регенерировать отдельные этапы

---

#### Test Case 5: Редактирование шаблона проекта

**Шаги:**
1. Dashboard → ⚙️ Настройки проекта
2. Изменить Story Template
3. Изменить Duration с 5 на 10
4. Сохранить
5. Создать новый ролик

**Ожидаемый результат:**
- [ ] Изменения сохранены
- [ ] Новые ролики используют обновленный шаблон
- [ ] Duration = 10 секунд

---

#### Test Case 6: Toggle Template Flag

**Шаги:**
1. Создать 2 ролика (1 template, 1 обычный)
2. На обычном ролике нажать "Сделать Template"
3. Проверить что is_template = true
4. Создать 3-й ролик → проверить что он обычный

**Ожидаемый результат:**
- [ ] Флаг переключается
- [ ] Badge "Template Video" появляется/исчезает
- [ ] Можно иметь несколько template videos

---

### 5.5 Cleanup и оптимизация

**Backend:**
- [ ] Удалить старые неиспользуемые файлы
- [ ] Проверить все imports
- [ ] Добавить error handling
- [ ] Добавить логирование

**Frontend:**
- [ ] Удалить старые компоненты (StoryForm, старый ProjectDetail)
- [ ] Проверить все imports
- [ ] Убрать console.log (оставить только для debug)
- [ ] Оптимизировать запросы (избежать лишних refetch)

**Database:**
- [ ] Проверить indexes на часто используемых полях
- [ ] Добавить constraints если нужно

---

### 5.6 Обновить документацию

**Файлы для обновления:**
- [ ] `CLAUDE.md` - обновить архитектуру, модели, workflow
- [ ] `README.md` - обновить описание проекта
- [ ] `backend/README.md` - обновить API endpoints
- [ ] `frontend/README.md` - обновить компоненты и страницы

---

## Проверка результата

**Финальный чеклист:**

### Backend
- [ ] Все модели созданы и работают
- [ ] Все API endpoints работают
- [ ] Relationships корректны
- [ ] AI генерация работает
- [ ] Автогенерация работает
- [ ] Нет критичных ошибок в логах

### Frontend
- [ ] Все страницы работают
- [ ] Навигация корректная
- [ ] Компоненты отрисовываются
- [ ] API запросы выполняются
- [ ] Нет ошибок в консоли браузера

### Integration
- [ ] Полный flow от создания проекта до публикации работает
- [ ] Template videos и обычные ролики работают корректно
- [ ] Автогенерация работает
- [ ] Approve/Reject работает
- [ ] Manual edit работает

### Performance
- [ ] Страницы загружаются быстро
- [ ] Нет лишних API запросов
- [ ] UI responsive

---

**Критерии приемки:**
- [ ] Все Test Cases пройдены успешно
- [ ] Система работает стабильно
- [ ] Нет критичных багов
- [ ] Код чистый и понятный
- [ ] Документация обновлена

---

**Статус:** ✅ Частично завершено (Core features implemented)

**Выполнено:**
- ✅ Task 05.1: Auto-generate-to-video endpoint реализован
  - Добавлен метод `generate_story_from_template` в openai_service
  - Endpoint `/auto-generate-to-video` создан
  - Последовательная генерация Steps 1-6
  - Сохранение generation_time_seconds для каждого этапа

- ✅ Task 05.2: Автогенерация интегрирована во фронтенд
  - useEffect для автозапуска генерации обычных роликов
  - UI индикатор прогресса генерации
  - UI блок Approve/Reject для финального видео
  - 4 кнопки: Approve, Regenerate, Manual Edit, Delete

- ✅ Task 05.3: Логика Approve → Adaptation → Publishing
  - После approve VIDEO автоматически запускается ADAPTATION
  - current_step переключается на PUBLISHING
  - status устанавливается в COMPLETED

**TODO (для будущей итерации):**
- [ ] Task 05.4: Тестирование полного flow (все 6 test cases)
- [ ] Task 05.5: Cleanup (удалить старые файлы, оптимизировать)
- [ ] Task 05.6: Обновить документацию (CLAUDE.md, README.md)
- [ ] Реализовать handleApproveVideo, handleQuickRegenerate, handleManualEdit
- [ ] Добавить логирование в критичных местах
- [ ] Проверить все imports и удалить неиспользуемые

**Готово к тестированию:**
Базовая функциональность реализована и готова к мануальному тестированию:
1. Создание проекта → AI генерация вариантов → выбор варианта
2. Автоматическая генерация обычных роликов (Steps 1-6)
3. Approve видео → автоматическая адаптация → COMPLETED

**Ответственный:** Full Stack Developer
