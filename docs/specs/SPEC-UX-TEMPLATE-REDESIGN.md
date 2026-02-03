# SPEC: Template Project UX Redesign

**Дата:** 2026-02-03
**Основа:** `docs/JTBD.md`, `docs/UX_AUDIT_TEMPLATE_WORKFLOW.md`
**Подход:** 3 экрана, организованных по jobs

---

## Проблема

Текущий UI организован по типам данных (Variants, Templates, Generations, Publishing). Пользователь думает задачами (настроить конвейер, запустить, проверить результат, следить за публикацией). Несовпадение создаёт трение на каждом шаге.

---

## Принцип

UI строится от Jobs To Be Done:

| Job | Суть | Частота |
|-----|------|---------|
| Setup + Generate | Настроить конвейер и запустить его | По необходимости |
| Moderation | Проверить результат, принять решение | Ежедневно |
| Monitor + Publish | Убедиться что система работает | Каждый вход |

Три jobs → три экрана. Каждый экран = одна задача пользователя.

---

## Текущие контроллы (полный реестр)

Ни один контролл не удаляется.

| # | Контролл | Компонент | Где сейчас |
|---|----------|-----------|-----------|
| 1 | Name, description, workspace select | `TemplateProjectForm` | Create modal |
| 2 | LLM model select | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 3 | Preprocessing prompt textarea | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 4 | Image model select, aspect ratio select | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 5 | Image prompt template textarea | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 6 | Video model select, duration select | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 7 | Video template name + prompt textarea | `TemplateProjectForm` / `VideoTemplatesList` | Create modal / Tab "Templates" |
| 8 | Social account selects (×3) | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 9 | CSV drag-drop, file picker, preview table | `CsvUpload` | Tab "Variants" |
| 10 | Variants table (search, inline edit, delete, pagination) | `VariantsList` | Tab "Variants" |
| 11 | Template cards (CRUD, set default) | `VideoTemplatesList` | Tab "Templates" |
| 12 | Schedule days buttons, time inputs, depth input | `PublishingConfigForm` | Tab "Publishing" |
| 13 | Variant select, template select, generate button | `GenerationPanel` | Tab "Generate" |
| 14 | Generations list (video preview, ratings, retry, delete) | `GenerationsList` | Tab "Generate" |
| 15 | Approve / reject / regenerate buttons | `ModerationQueue` | Tab "Moderation" |
| 16 | Reject reason input, comment textarea | `ModerationQueue` (modal) | Tab "Moderation" |
| 17 | Regenerate feedback textarea | `ModerationQueue` (modal) | Tab "Moderation" |
| 18 | Rejection archive list | `RejectionArchive` | Tab "Moderation" |
| 19 | Schedule slot cards grid, video preview modal | `PublishingScheduleView` | Tab "Publishing" |
| 20 | Queue items list, metadata edit, delete | `PublishingQueueView` | Tab "Publishing" |

---

## Новая структура: 3 экрана

```
┌──────────────────────────────────────────────────────────┐
│  Project Name                                    ⚙️       │
├──────────────────────────────────────────────────────────┤
│  [ Dashboard  ·  Review (5)  ·  Pipeline ]               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Screen content                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Карта перемещений

| # | Контролл | Было | Стало |
|---|----------|------|-------|
| 1 | Project name/desc/workspace | Create modal | Create modal (без изменений) |
| 2-6 | Models, prompts, aspect ratio, duration | Create modal + Settings | **Pipeline** screen: pipeline steps |
| 7 | Video templates (CRUD) | Tab "Templates" | **Pipeline** screen: Video step |
| 8 | Social accounts | Create modal + Settings | **Pipeline** screen: Output step |
| 9 | CSV upload | Tab "Variants" | **Pipeline** screen: Input step |
| 10 | Variants table | Tab "Variants" | **Pipeline** screen: Input step |
| 11 | Template cards | Tab "Templates" | **Pipeline** screen: Video step |
| 12 | Schedule config | Tab "Publishing" | **Pipeline** screen: Output step |
| 13 | Generate controls | Tab "Generate" | **Pipeline** screen: Run controls |
| 14 | Generations list | Tab "Generate" | **Pipeline** screen: Run history |
| 15-17 | Moderation actions | Tab "Moderation" | **Review** screen |
| 18 | Rejection archive | Tab "Moderation" | **Review** screen |
| 19 | Schedule calendar | Tab "Publishing" | **Dashboard** screen |
| 20 | Queue list | Tab "Publishing" | **Dashboard** screen |

---

## Screen 1: Dashboard

### Job
Monitor (5) + Publish (4): "Видеть состояние системы одним взглядом. Убедиться что публикация идёт."

### Когда открывается
Default screen. Пользователь заходит в проект → видит Dashboard.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Pipeline Status                                             │
│                                                              │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌────────┐│
│  │ Generating│ → │  Review   │ → │ Approved  │ → │Schedule││
│  │     3     │   │   ● 5     │   │    12     │   │ 12/14  ││
│  └───────────┘   └───────────┘   └───────────┘   └────────┘│
│                                                              │
│  ✅ Next publish: Mon 3 Feb, 18:00                           │
│  ⚠️ 2 empty slots — review more or run pipeline              │
│                                                              │
│  [ → Review 5 videos ]  [ → Run pipeline ]                   │
├──────────────────────────────────────────────────────────────┤
│  Schedule                              [ Calendar | Queue ]  │
│                                                              │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│  │ Mon 3  │ │ Wed 5  │ │ Fri 7  │ │ Mon 10 │ │ Wed 12 │    │
│  │ 18:00  │ │ 18:00  │ │ 18:00  │ │ 18:00  │ │ 18:00  │    │
│  │[thumb] │ │[thumb] │ │[thumb] │ │[empty] │ │[empty] │    │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Содержимое

**1. Pipeline Funnel**

Четыре блока-счётчика, каждый кликабелен:
- Generating → переход на Pipeline (Run history)
- Review → переход на Review
- Approved → переход на Queue (ниже)
- Schedule → scroll к календарю

**2. Status + Actions**

Контекстные messages и кнопки:
- "Review N videos →" — если есть pending moderation
- "Run pipeline →" — если мало контента
- Warnings: пустые слоты, нет платформ, failed publishes

**3. Schedule Calendar**

Компоненты: `PublishingScheduleView` + `PublishingQueueView` (toggle Calendar/Queue).

Те же компоненты что сейчас на Publishing tab, перенесены сюда. Это основное место где пользователь видит расписание.

### Состояние: новый проект

Когда pipeline не настроен (нет variants или templates), Dashboard показывает onboarding:

```
┌──────────────────────────────────────────────────────────────┐
│  Pipeline Status                                             │
│                                                              │
│  ⚠️ Pipeline not configured                                  │
│                                                              │
│  Set up your pipeline to start generating videos:            │
│  [ → Open Pipeline Setup ]                                   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  Schedule                                                    │
│                                                              │
│  No schedule configured.                                     │
│  Configure days and times in Pipeline → Output settings.     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Одна кнопка ведёт на Pipeline screen. Без чеклистов — Pipeline сам покажет что настроить.

---

## Screen 2: Review

### Job
Moderation (3): "Быстро просмотреть и решить: одобрить / перегенерировать / отклонить."

### Ключевое изменение

Вместо скроллящегося списка — **focused review**: одно видео в фокусе, с навигацией между элементами.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Review                                          3 of 8      │
│                                                              │
│  ┌───────────────────┐    Variant data                       │
│  │                   │    ─────────────                       │
│  │                   │    ethnicity: Asian                    │
│  │                   │    car: Lamborghini                    │
│  │   [video 9:16]    │    city: Dubai                        │
│  │                   │                                       │
│  │                   │    Template: "Default"                 │
│  │                   │                                       │
│  │                   │    ─────────────                       │
│  │                   │    Publish to:                         │
│  │                   │    📅 Wed 5 Feb, 18:00                │
│  │                   │    Slot 7 of 14                        │
│  └───────────────────┘                                       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐       │
│  │ ✗ Reject │  │ ↻ Redo   │  │  ✓ Approve → Wed 18h │       │
│  └──────────┘  └──────────┘  └──────────────────────┘       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [thumb1] [thumb2] [■thumb3■] [thumb4] ... [thumb8]    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [ Rejection Archive ▸ ]                                     │
└──────────────────────────────────────────────────────────────┘
```

### Элементы

**Центральная область — одно видео:**
- Video preview (9:16, крупный)
- Variant data (key-value из CSV)
- Template name
- **Target slot** — показывает куда попадёт видео при approve. Видна ДО нажатия кнопки, не в confirmation modal.

**Кнопки действий:**
- **Reject** — раскрывает inline-форму (reason + comment) прямо под кнопками, без модалки
- **Redo** (Regenerate) — раскрывает inline-форму (feedback textarea) прямо под кнопками
- **Approve → Wed 18h** — кнопка сразу показывает куда пойдёт видео. Один клик = approve. Без confirmation modal (вся информация уже на экране).

**Filmstrip (внизу):**
- Горизонтальная полоса thumbnails всех pending видео
- Текущее видео подсвечено
- Клик по thumbnail = переключение
- Keyboard: ← → для навигации

**Счётчик:**
- "3 of 8" — текущая позиция в очереди
- Обновляется при approve/reject (элемент уходит, следующий становится текущим)

**Rejection Archive:**
- Свёрнутая секция внизу
- Клик раскрывает список отклонённых видео

### Состояние: пустая очередь

```
┌──────────────────────────────────────────────────────────────┐
│  Review                                                      │
│                                                              │
│  ✅ All caught up! No videos pending review.                 │
│                                                              │
│  [ → Run pipeline ]    [ → Dashboard ]                       │
│                                                              │
│  [ Rejection Archive ▸ ]                                     │
└──────────────────────────────────────────────────────────────┘
```

### Slot calculation

Target slot вычисляется так:
1. Загрузить текущий schedule (`GET /publishing-schedule`)
2. Посчитать сколько видео уже в queue (approved)
3. Следующий пустой slot = slots[queue_length]
4. Если пустых слотов нет → показать "All slots filled. Video will queue for next available slot."

При каждом approve slot пересчитывается для следующего видео.

---

## Screen 3: Pipeline

### Jobs
Setup (1) + Batch Generation (2): "Настроить конвейер один раз, запускать по необходимости."

### Ключевое изменение

Вместо разрозненных табов (Variants, Templates, Settings, Generate) — единый экран, показывающий pipeline как цельный процесс. Две секции: **Configure** (настройка шагов) и **Run** (запуск и история).

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Pipeline                                                    │
│                                                              │
│  ┌─ Configure ─────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │  ┌─────────┐  ┌──────────────┐  ┌─────────┐  ┌──────┐ │ │
│  │  │  Input  │→ │Preprocessing │→ │  Image  │→ │Video │→...│
│  │  │ 47 vars │  │ GPT-4o-mini  │  │flux-pro │  │veo3.1│ │ │
│  │  │         │  │              │  │ 9:16    │  │2 tmpl│ │ │
│  │  └────┬────┘  └──────┬───────┘  └────┬────┘  └──┬───┘ │ │
│  │       ↓              ↓               ↓           ↓     │ │
│  │  [expanded          [collapsed]  [collapsed] [collapsed]│ │
│  │   step details]                                         │ │
│  │                                                         │ │
│  │  ...→ ┌──────────┐                                     │ │
│  │       │  Output   │                                     │ │
│  │       │ YT + IG   │                                     │ │
│  │       │Mon/Wed/Fri│                                     │ │
│  │       └──────────┘                                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ Run ───────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │  Materials: 47 variants (23 unused)                     │ │
│  │  Template:  [ Default ▾ ]                               │ │
│  │                                                         │ │
│  │  ┌─ Select variants ─────────────────────────────────┐  │ │
│  │  │  ● All unused (23)                                 │  │ │
│  │  │  ○ Least used (top N)                              │  │ │
│  │  │  ○ Specific variants...                            │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                         │ │
│  │  [ ▶ Run — 23 videos ]                                  │ │
│  │                                                         │ │
│  │  ─────────────────────────────────────────────────────  │ │
│  │  History                                                │ │
│  │  ▸ Batch #3: 10/10 ✅  — Mon 3 Feb                     │ │
│  │  ▸ Batch #2: 8/10 ⚠️   — Sun 2 Feb                     │ │
│  │  ▸ Batch #1: 5/5 ✅    — Sat 1 Feb                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Секция: Configure

**Pipeline visualization** — горизонтальная цепочка шагов:

```
Input → Preprocessing → Image → Video → Output
```

Каждый шаг — карточка с summary (модель, количество, ключевой параметр).

**Клик по шагу** — раскрывает настройки этого шага inline (accordion). Только один шаг раскрыт одновременно.

#### Step: Input

**Summary:** `47 variants`
**Раскрытое содержимое:**
- CSV upload (drag-drop zone) — компонент `CsvUpload`
- Variants table (search, edit, delete, pagination) — компонент `VariantsList`
- Контроллы #9, #10

#### Step: Preprocessing

**Summary:** `GPT-4o-mini`
**Раскрытое содержимое:**
- LLM model select
- Preprocessing prompt textarea
- Контроллы #2, #3

#### Step: Image

**Summary:** `flux-pro · 9:16`
**Раскрытое содержимое:**
- Image model select
- Aspect ratio select
- Image prompt template textarea
- Контроллы #4, #5

#### Step: Video

**Summary:** `veo3.1 · 2 templates`
**Раскрытое содержимое:**
- Video model select
- Duration select
- Video templates list (CRUD, set default) — компонент `VideoTemplatesList`
- Контроллы #6, #7, #11

#### Step: Output

**Summary:** `YouTube + Instagram · Mon/Wed/Fri 18:00`
**Раскрытое содержимое:**
- Social account selects (×3 платформы)
- Schedule config (days, times, depth) — компонент `PublishingConfigForm`
- Контроллы #8, #12

### Секция: Run

**Production controls:**
- Variant selection (all unused / least used / specific)
- Template select
- Run button с count
- Контроллы #13

**History:**
- Генерации сгруппированы по batch (или single = batch of 1)
- Каждый batch раскрывается → список генераций с превью, рейтингами, статусами
- Контроллы #14

### Состояние: новый проект

Pipeline steps показывают что настроено, что нет:

```
┌─────────┐  ┌──────────────┐  ┌─────────┐  ┌──────┐  ┌──────┐
│  Input  │→ │Preprocessing │→ │  Image  │→ │Video │→ │Output│
│ ❌ 0 var│  │ ✅ GPT-4o-m  │  │ ✅ flux │  │✅ 1tm│  │ ❌    │
└─────────┘  └──────────────┘  └─────────┘  └──────┘  └──────┘
```

Run секция disabled с message: "Upload variants to start generating."

Пользователь видит: Input нужно заполнить (CSV), Output нужно настроить (social + schedule). Остальное уже задано при создании проекта.

### Settings page

Settings page (`/project/:id/edit`) сохраняется для базовых настроек проекта:
- Name, description, workspace

Все остальные настройки (модели, промпты, шаблоны, соцсети, расписание) живут на Pipeline screen. Settings page становится lightweight.

---

## Smart Default Screen

| Состояние проекта | Default screen |
|-------------------|----------------|
| Pipeline не настроен (нет variants) | **Pipeline** (нужно настроить) |
| Pipeline настроен, нет генераций | **Pipeline** (нужно запустить) |
| Есть pending moderation | **Review** (нужно модерировать) |
| Всё обработано, pipeline работает | **Dashboard** (мониторинг) |

Логика: открываем тот экран, где пользователю нужно действовать.

---

## Переходы между экранами

```
CREATE PROJECT (modal)
│
│  Создаёт: project + models + prompts + 1 template
│  Не создаёт: variants, social accounts, schedule
│
├─→ Pipeline screen (default для нового проекта)
│   │
│   ├─ Input step: upload CSV → 47 variants ✅
│   ├─ Output step: connect social + configure schedule ✅
│   │
│   ├─ Run: select variants → [ ▶ Run — 10 videos ]
│   │   └─ 10 generations start, progress in History
│   │
│   └─ Generations complete → badge on Review tab: "Review (10)"
│
├─→ Review screen
│   │
│   ├─ Видим видео #1 of 10
│   ├─ Target slot: "→ Mon 3 Feb, 18:00"
│   ├─ [ ✓ Approve → Mon 18h ] → видео уходит в queue, показывается #2
│   ├─ [ ✗ Reject ] → inline reason form → видео в архив, показывается #2
│   ├─ [ ↻ Redo ] → inline feedback → новая генерация, показывается #2
│   │
│   └─ Все обработаны → "All caught up!" → [ → Dashboard ]
│
├─→ Dashboard screen
│   │
│   ├─ Pipeline funnel: Generating 0 · Review 0 · Approved 8 · Schedule 8/14
│   ├─ Calendar: слоты с thumbnails
│   ├─ Status: "Next publish: Mon 3 Feb, 18:00"
│   ├─ Warning: "6 empty slots — run pipeline or review more"
│   │
│   └─ Quick actions → ведут на Pipeline или Review
│
└─ APScheduler publishes at slot times → Dashboard shows results
```

---

## Полная карта контроллов → экраны

| # | Контролл | Screen | Секция |
|---|----------|--------|--------|
| 1 | Project name/desc/workspace | Create modal (без изменений) | — |
| 2 | LLM model select | **Pipeline** | Configure → Preprocessing step |
| 3 | Preprocessing prompt textarea | **Pipeline** | Configure → Preprocessing step |
| 4 | Image model select, aspect ratio | **Pipeline** | Configure → Image step |
| 5 | Image prompt template textarea | **Pipeline** | Configure → Image step |
| 6 | Video model select, duration | **Pipeline** | Configure → Video step |
| 7 | Video template CRUD | **Pipeline** | Configure → Video step |
| 8 | Social account selects | **Pipeline** | Configure → Output step |
| 9 | CSV upload | **Pipeline** | Configure → Input step |
| 10 | Variants table | **Pipeline** | Configure → Input step |
| 11 | Template cards (set default) | **Pipeline** | Configure → Video step |
| 12 | Schedule config (days/times/depth) | **Pipeline** | Configure → Output step |
| 13 | Variant select + template select + run button | **Pipeline** | Run |
| 14 | Generations list (preview, ratings, retry) | **Pipeline** | Run → History |
| 15 | Approve / reject / regenerate buttons | **Review** | Action buttons |
| 16 | Reject reason + comment | **Review** | Inline form (expand on reject) |
| 17 | Regenerate feedback textarea | **Review** | Inline form (expand on redo) |
| 18 | Rejection archive | **Review** | Collapsible section |
| 19 | Schedule calendar + video preview modal | **Dashboard** | Schedule section |
| 20 | Queue list + metadata edit | **Dashboard** | Schedule section (toggle) |

Каждый существующий контролл имеет чёткое место. Ничего не потеряно.

---

## Что меняется vs текущий UI

| Аспект | Сейчас | Станет |
|--------|--------|--------|
| Навигация | 5 табов по типу данных | 3 экрана по задачам |
| Settings | Отдельная страница со всем | Pipeline screen + lightweight settings (name only) |
| Variants | Отдельный таб | Pipeline → Input step |
| Templates | Отдельный таб | Pipeline → Video step |
| Publishing config | Publishing tab | Pipeline → Output step |
| Calendar | Publishing tab | Dashboard screen |
| Generation | Отдельный таб с panel + list | Pipeline → Run section |
| Moderation | Список карточек | Focused review (one-at-a-time) |
| Slot info при approve | Нет | Видна сразу на Review screen |
| Batch generation | Нет | Pipeline → Run (default mode) |
| Pipeline overview | Нет | Dashboard screen (funnel) |
| Smart default screen | Нет (всегда Generate tab) | Зависит от состояния проекта |

---

## Scope

| # | Изменение | Новые компоненты |
|---|-----------|------------------|
| 1 | 3-screen navigation (Dashboard, Review, Pipeline) | `TemplateProjectView` refactor |
| 2 | Dashboard: pipeline funnel + calendar | `PipelineFunnel`, reuse `PublishingScheduleView` |
| 3 | Review: focused one-at-a-time + filmstrip | `FocusedReview`, `Filmstrip` |
| 4 | Review: target slot display + inline reject/redo forms | Modify `ModerationQueue` |
| 5 | Pipeline Configure: step visualization + accordion | `PipelineSteps`, `PipelineStep` |
| 6 | Pipeline Run: batch controls + grouped history | Modify `GenerationPanel`, `GenerationsList` |
| 7 | Smart default screen logic | `TemplateProjectView` |
| 8 | Pipeline stats API | Backend endpoint |

### Рекомендуемый порядок

**Phase 1 — Navigation + Dashboard:**
3 экрана, pipeline funnel, перенос calendar на Dashboard. Быстрый structural win.

**Phase 2 — Review:**
Focused review, filmstrip, target slot, inline forms. Главный ежедневный экран.

**Phase 3 — Pipeline:**
Step visualization, accordion settings, batch controls, grouped history. Самый объёмный.

---

## Не в scope

- Drag-drop reorder очереди
- Drag-drop видео между слотами
- Multi-level approval workflow
- Analytics / metrics dashboard
- Auto-generation при пустой очереди (T23)
- Keyboard shortcuts для Review (←→ навигация, hotkeys для approve/reject)
