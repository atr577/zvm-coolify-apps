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

## Ключевые решения (Q1-Q12)

| # | Вопрос | Решение |
|---|--------|---------|
| Q1 | Create modal scope | Name + workspace only. Модели/промпты → Pipeline |
| Q2 | Heavy steps (Variants, Templates) | Accordion inline. Все шаги в одном паттерне |
| Q3 | Save behavior | Sticky Save bar. Появляется при наличии изменений |
| Q4 | Single generation | Test per step (кнопка Test на каждом аккордеоне) + Run для batch |
| Q5 | Ratings | Убрать. Только approve/reject/regenerate |
| Q6 | Review position | Первый непросмотренный при повторном заходе |
| Q7 | Pause publishing | Dashboard (toggle) + Pipeline→Distribution (полные настройки) |
| Q8 | Queue metadata | При approve в Review (заполнить) + Dashboard по клику (редактировать) |
| Q9 | Smart default screen | Всегда smart: нет вариантов→Pipeline, есть на модерации→Review, иначе→Dashboard |
| Q10 | Output step naming | **Distribution** (каналы распространения) |
| Q11 | Configure summary line | Иконки + ключевое значение (`✅ Image: flux-pro · 9:16`) |
| Q12 | Filmstrip navigation | Horizontal scroll + фильтры (All/Pending/Approved/Rejected) |
| Q13 | Connect new account | Inline OAuth: кнопка "+" рядом с каждым селектом в Distribution |
| Q14 | Placeholder hints | Кликабельные теги {var} под каждым prompt textarea (после загрузки CSV) |
| Q15 | Dashboard onboarding | Оставить как подстраховку при ручном переходе |
| Q16 | Distribution Test | Проверка аккаунтов: подключены, работают, не забанены |
| Q17 | Redo lifecycle | Item уходит из Pending, авто-переход на следующий, regenerated → конец очереди |

---

## Текущие контроллы (полный реестр)

Ни один контролл не удаляется. Ratings (#14 звёзды) удаляются по решению Q5.

| # | Контролл | Компонент | Где сейчас |
|---|----------|-----------|-----------|
| 1 | Name, description, workspace select | `TemplateProjectForm` | Create modal |
| 2 | LLM model select | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 3 | Preprocessing prompt textarea | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 4 | Image model select, aspect ratio select | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 5 | Image prompt template textarea | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 6 | Video model select, duration select | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 7 | Video template name + prompt textarea | `TemplateProjectForm` / `VideoTemplatesList` | Create modal / Templates tab |
| 8 | Social account selects (×3) | `TemplateProjectForm` / `TemplateSettingsForm` | Create modal / Settings |
| 9 | CSV drag-drop, file picker, preview table | `CsvUpload` | Tab "Variants" |
| 10 | Variants table (search, inline edit, delete, pagination) | `VariantsList` | Tab "Variants" |
| 11 | Template cards (CRUD, set default) | `VideoTemplatesList` | Tab "Templates" |
| 12 | Schedule days buttons, time inputs, depth input | `PublishingConfigForm` | Tab "Publishing" |
| 13 | Variant select, template select, generate button | `GenerationPanel` | Tab "Generate" |
| 14 | Generations list (video preview, ~~ratings~~, retry, delete) | `GenerationsList` | Tab "Generate" |
| 15 | Approve / reject / regenerate buttons | `ModerationQueue` | Tab "Moderation" |
| 16 | Reject reason input, comment textarea | `ModerationQueue` (modal) | Tab "Moderation" |
| 17 | Regenerate feedback textarea | `ModerationQueue` (modal) | Tab "Moderation" |
| 18 | Rejection archive list | `RejectionArchive` | Tab "Moderation" |
| 19 | Schedule slot cards grid, video preview modal | `PublishingScheduleView` | Tab "Publishing" |
| 20 | Queue items list, metadata edit, delete | `PublishingQueueView` | Tab "Publishing" |

---

## Create Project (Q1)

Модалка создания проекта содержит **только**:
- Project name
- Workspace select

Description, модели, промпты, шаблоны, соцсети, расписание — **не в create modal**. Description доступен на Settings page. Остальное — на Pipeline screen. Новый проект открывается сразу на Pipeline с дефолтными значениями в Configure.

**Дефолты при создании:**
- LLM: gpt-4o-mini
- Image: flux-pro, 9:16
- Video: veo3.1, 5s
- 1 пустой video template
- Остальное пусто (CSV, social accounts, schedule)

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
| 1 | Project name/desc/workspace | Create modal | Create modal (name + workspace only) |
| 2-6 | Models, prompts, aspect ratio, duration | Create modal + Settings | **Pipeline** → Configure steps |
| 7 | Video templates (CRUD) | Tab "Templates" | **Pipeline** → Configure → Video step |
| 8 | Social accounts | Create modal + Settings | **Pipeline** → Configure → Distribution step |
| 9 | CSV upload | Tab "Variants" | **Pipeline** → Configure → Input step |
| 10 | Variants table | Tab "Variants" | **Pipeline** → Configure → Input step |
| 11 | Template cards | Tab "Templates" | **Pipeline** → Configure → Video step |
| 12 | Schedule config | Tab "Publishing" | **Pipeline** → Configure → Distribution step |
| 13 | Generate controls | Tab "Generate" | **Pipeline** → Run controls |
| 14 | Generations list | Tab "Generate" | **Pipeline** → Run history |
| 15-17 | Moderation actions | Tab "Moderation" | **Review** screen |
| 18 | Rejection archive | Tab "Moderation" | **Review** screen |
| 19 | Schedule calendar | Tab "Publishing" | **Dashboard** screen |
| 20 | Queue list + metadata | Tab "Publishing" | **Dashboard** screen + **Review** (при approve) |

---

## Screen 1: Dashboard

### Job
Monitor (5) + Publish (4): "Видеть состояние системы одним взглядом. Убедиться что публикация идёт."

### Когда открывается
Default screen при smart logic (Q9): когда pipeline настроен, генерации есть, модерация пуста.

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
│  Schedule                  ⏸️ Pause   [ Calendar | Queue ]   │
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
- Approved → scroll к Queue (ниже)
- Schedule → scroll к календарю

**2. Status + Actions**

Контекстные messages и кнопки:
- "Review N videos →" — если есть pending moderation
- "Run pipeline →" — если мало контента
- Warnings: пустые слоты, нет платформ, failed publishes

**3. Pause Publishing (Q7)**

Toggle "Pause" рядом с заголовком Schedule section. При активации:
- Публикация приостанавливается (APScheduler пропускает слоты)
- Visual indicator: жёлтая плашка "Publishing paused"
- Toggle также доступен на Pipeline → Distribution step

**4. Schedule Calendar + Queue**

Компоненты: `PublishingScheduleView` + `PublishingQueueView` (toggle Calendar/Queue).
Те же компоненты что сейчас на Publishing tab, перенесены сюда.

**Клик по заполненному слоту** (Q8) → drawer/popup с:
- Video preview
- Метаданные (title, description, hashtags) — **редактируемые**
- Кнопка Remove from queue

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
│  Configure days and times in Pipeline → Distribution.        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Screen 2: Review

### Job
Moderation (3): "Быстро просмотреть и решить: одобрить / перегенерировать / отклонить."

### Ключевое изменение

Вместо скроллящегося списка — **focused review**: одно видео в фокусе, с навигацией между элементами.

### Позиция при входе (Q6)

При повторном заходе на Review screen — автоматический переход на **первый непросмотренный** (unreviewed) item. Прогресс = позиция.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Review                                          3 of 8      │
│                                                              │
│  [ All (8) | Pending (5) | Approved (2) | Rejected (1) ]    │
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
│  ┌─ Metadata (title, description, hashtags) ────────────┐   │
│  │  Title: [auto-generated, editable]                    │   │
│  │  Description: [auto-generated, editable]              │   │
│  │  Hashtags: [auto-generated, editable]                 │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [thumb1] [thumb2] [■thumb3■] [thumb4] ... [thumb8]    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [ Rejection Archive ▸ ]                                     │
└──────────────────────────────────────────────────────────────┘
```

### Элементы

**Filters (Q12):**
- Горизонтальные фильтры над контентом: All / Pending / Approved / Rejected
- Фильтр влияет на filmstrip и счётчик
- По умолчанию: Pending (показывает только нерассмотренные)

**Центральная область — одно видео:**
- Video preview (9:16, крупный)
- Variant data (key-value из CSV)
- Template name
- **Target slot** — показывает куда попадёт видео при approve. Видна ДО нажатия кнопки.

**Metadata при approve (Q8):**
- Поля title / description / hashtags показаны под кнопками действий
- Auto-generated значения (заполнены), пользователь может отредактировать перед approve
- При Approve метаданные сохраняются вместе с видео в queue

**Центральная область — дополнительно:**
- **"View source image" link** — ссылка для просмотра исходной картинки (из которой сгенерировано видео). Открывает в новой вкладке.

**Кнопки действий:**
- **Reject** — раскрывает inline-форму (reason + comment) прямо под кнопками, без модалки
- **Redo** (Regenerate) — раскрывает inline-форму (feedback textarea) прямо под кнопками
- **Approve → Wed 18h** — кнопка показывает куда пойдёт видео. Один клик = approve с текущими metadata. Без confirmation modal.

**Redo lifecycle (Q17):**
- При Redo → item **уходит из Pending** (как при Reject)
- Авто-переход на следующий Pending item
- Когда regeneration завершится → **новый item появляется в конце** Pending очереди
- Счётчик обновляется (N уменьшается при Redo, увеличивается когда regeneration завершена)

**Filmstrip (Q12):**
- Горизонтальная полоса thumbnails
- Horizontal scroll для 50+ items
- Фильтруется по выбранному фильтру (All/Pending/Approved/Rejected)
- Текущее видео подсвечено рамкой
- Клик по thumbnail = переключение
- Keyboard: ← → для навигации
- Approved thumbnails = зелёная обводка, Rejected = красная, Pending = без обводки

**Счётчик:**
- "3 of 8" — текущая позиция в отфильтрованном списке
- Обновляется при approve/reject (элемент уходит из Pending, следующий становится текущим)

**Rejection Archive:**
- Свёрнутая секция внизу
- Клик раскрывает список отклонённых видео
- Pagination (Previous/Next) для длинных списков

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

Вместо разрозненных табов (Variants, Templates, Settings, Generate) — единый экран, показывающий pipeline как цельный процесс. Две секции: **Configure** (настройка шагов, свёрнута по умолчанию) и **Run** (запуск и история, видна сразу).

### Layout (Variant A: Configure collapsed, Run first)

```
┌──────────────────────────────────────────────────────────────┐
│  Pipeline                                                    │
│                                                              │
│  ┌─ Configure ──────────────────────────── [ ▾ Expand ] ───┐ │
│  │  ✅ Input: 47 vars · ✅ Preproc: GPT-4o-mini ·          │ │
│  │  ✅ Image: flux-pro · 9:16 · ✅ Video: veo3.1 · 2 tmpl · │ │
│  │  ❌ Distribution: no accounts                             │ │
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

**По умолчанию свёрнута** — показывает summary line (Q11):

```
✅ Input: 47 vars · ✅ Preproc: GPT-4o-mini · ✅ Image: flux-pro · 9:16 · ✅ Video: veo3.1 · 2 tmpl · ❌ Distribution: no accounts
```

Каждый шаг = иконка статуса + ключевое значение. Пользователь сразу видит что настроено, что нет.

**При раскрытии** — горизонтальная цепочка шагов pipeline:

```
Input → Preprocessing → Image → Video → Distribution
```

Каждый шаг — карточка с summary. Клик по шагу раскрывает настройки inline (accordion, один за раз).

**Sticky Save Bar (Q3):**
- Появляется внизу экрана при наличии несохранённых изменений в любом шаге
- Показывает: "Unsaved changes" + кнопка `[ Save ]` + кнопка `[ Discard ]`
- Исчезает после Save/Discard
- Sticky — видна при скролле

#### Step: Input

**Summary:** `47 variants`
**Раскрытое содержимое:**
- CSV upload (drag-drop zone) — компонент `CsvUpload`
- Variants table (search, edit, delete, pagination) — компонент `VariantsList`
- **Test button (Q4):** "Test" → показывает parsed CSV preview: какие переменные, сколько строк, превью первых 5 строк
- Контроллы #9, #10

#### Step: Preprocessing

**Summary:** `GPT-4o-mini`
**Раскрытое содержимое:**
- LLM model select
- Preprocessing prompt textarea
- **Placeholder hints (Q14):** кликабельные теги `{column_name}` под textarea. Появляются после загрузки CSV в Input step. Клик → копирует в буфер.
- **Test button (Q4):** "Test" → берёт 1 случайный вариант, подставляет в промпт-шаблон, показывает итоговый промпт (текст)
- Контроллы #2, #3

#### Step: Image

**Summary:** `flux-pro · 9:16`
**Раскрытое содержимое:**
- Image model select
- Aspect ratio select
- Image prompt template textarea
- **Placeholder hints (Q14):** кликабельные теги `{column_name}` и `{preprocessing_result}` под textarea. Появляются после загрузки CSV.
- **Test button (Q4):** "Test" → генерирует 1 картинку по текущим настройкам + промпту из случайного варианта. Показывает результат inline.
- Контроллы #4, #5

#### Step: Video

**Summary:** `veo3.1 · 2 templates`
**Раскрытое содержимое:**
- Video model select
- Duration select
- Video templates list (CRUD, set default) — компонент `VideoTemplatesList`
- **Test button (Q4):** "Test" → генерирует 1 видео из тестовой картинки (или последней Test Image). Показывает результат inline.
- Контроллы #6, #7, #11

#### Step: Distribution (Q10)

**Summary:** `YouTube + Instagram · Mon/Wed/Fri 18:00`
**Раскрытое содержимое:**
- Social account selects (×3 платформы) + **кнопка "+" рядом с каждым селектом** (Q13) — запускает inline OAuth flow для подключения нового аккаунта
- Schedule config (days, times, depth) — компонент `PublishingConfigForm`
- **Pause publishing toggle (Q7)** — тот же toggle что на Dashboard
- **Test button (Q16):** "Check" → проверяет подключённые аккаунты (активны, не забанены, токены валидны). Показывает checklist результат inline.
- Контроллы #8, #12

### Секция: Run

**Production controls:**
- Variant selection (all unused / least used / specific)
- Template select
- Run button с count
- Контроллы #13

**History:**
- Генерации сгруппированы по batch
- Каждый batch раскрывается → список генераций с превью, статусами, retry, delete
- **Кликабельные превью** — image и video артефакты открываются по клику (image в новой вкладке, video — inline play)
- **Без ratings** (Q5) — только статус (completed/failed/cancelled) + action buttons
- **Pagination** — Previous/Next или "Load more" для длинных списков
- Контроллы #14 (без звёзд)

### Состояние: новый проект

Configure раскрыт автоматически. Summary line показывает статусы:

```
✅ Preproc: GPT-4o-mini · ✅ Image: flux-pro · 9:16 · ✅ Video: veo3.1 · 1 tmpl · ❌ Input: no CSV · ❌ Distribution: no accounts
```

Run секция disabled с message: "Upload variants to start generating."

Пользователь видит: Input нужно заполнить (CSV), Distribution нужно настроить. Остальное уже задано дефолтами.

### Settings page

Settings page (`/project/:id/edit`) сохраняется для:
- Project name
- Project description
- Workspace

Все pipeline-настройки (модели, промпты, шаблоны, соцсети, расписание) живут на Pipeline screen. Settings page становится lightweight.

---

## Smart Default Screen (Q9)

Всегда smart — выбирает экран по состоянию проекта:

| Состояние проекта | Default screen | Почему |
|-------------------|----------------|--------|
| Нет variants | **Pipeline** (Configure раскрыт) | Нужно настроить |
| Есть variants, нет генераций | **Pipeline** (Run в фокусе) | Нужно запустить |
| Есть pending moderation | **Review** | Нужно модерировать |
| Всё обработано, pipeline работает | **Dashboard** | Мониторинг |

Логика: открываем тот экран, где пользователю нужно действовать.

---

## Переходы между экранами

```
CREATE PROJECT (modal: name + workspace only)
│
│  Создаёт: project с дефолтными моделями
│  Не создаёт: variants, social accounts, schedule
│
├─→ Pipeline screen (default для нового проекта, Configure раскрыт)
│   │
│   ├─ Input step: upload CSV → 47 variants ✅
│   ├─ Distribution step: connect social + configure schedule ✅
│   ├─ [Save] — sticky bar сохраняет все изменения
│   │
│   ├─ Test per step (Q4):
│   │   ├─ Test Input → parsed CSV preview
│   │   ├─ Test Preprocessing → generated prompt text
│   │   ├─ Test Image → 1 generated image
│   │   ├─ Test Video → 1 generated video
│   │   └─ Test Distribution → full pipeline for 1 variant
│   │
│   ├─ Run: select variants → [ ▶ Run — 10 videos ]
│   │   └─ 10 generations start, progress in History
│   │
│   └─ Generations complete → badge on Review tab: "Review (10)"
│
├─→ Review screen (opens at first unreviewed item)
│   │
│   ├─ Filters: All / Pending / Approved / Rejected
│   ├─ Видим видео #1 of 10
│   ├─ Target slot: "→ Mon 3 Feb, 18:00"
│   ├─ Metadata fields: title, description, hashtags (editable)
│   ├─ [ ✓ Approve → Mon 18h ] → видео + metadata в queue, показывается #2
│   ├─ [ ✗ Reject ] → inline reason form → видео в архив, показывается #2
│   ├─ [ ↻ Redo ] → inline feedback → новая генерация, показывается #2
│   │
│   └─ Все обработаны → "All caught up!" → [ → Dashboard ]
│
├─→ Dashboard screen
│   │
│   ├─ Pipeline funnel: Generating 0 · Review 0 · Approved 8 · Schedule 8/14
│   ├─ Calendar: слоты с thumbnails (клик → drawer с metadata editing)
│   ├─ Pause publishing toggle (Q7)
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
| 1 | Project name/desc/workspace | Create modal (name + workspace) + Settings (full edit) | — |
| 2 | LLM model select | **Pipeline** | Configure → Preprocessing |
| 3 | Preprocessing prompt textarea | **Pipeline** | Configure → Preprocessing |
| 4 | Image model select, aspect ratio | **Pipeline** | Configure → Image |
| 5 | Image prompt template textarea | **Pipeline** | Configure → Image |
| 6 | Video model select, duration | **Pipeline** | Configure → Video |
| 7 | Video template CRUD | **Pipeline** | Configure → Video |
| 8 | Social account selects | **Pipeline** | Configure → Distribution |
| 9 | CSV upload | **Pipeline** | Configure → Input |
| 10 | Variants table | **Pipeline** | Configure → Input |
| 11 | Template cards (set default) | **Pipeline** | Configure → Video |
| 12 | Schedule config (days/times/depth) | **Pipeline** | Configure → Distribution |
| 13 | Variant select + template select + run button | **Pipeline** | Run |
| 14 | Generations list (preview, retry) — без ratings | **Pipeline** | Run → History |
| 15 | Approve / reject / regenerate buttons | **Review** | Action buttons |
| 16 | Reject reason + comment | **Review** | Inline form (expand on reject) |
| 17 | Regenerate feedback textarea | **Review** | Inline form (expand on redo) |
| 18 | Rejection archive | **Review** | Collapsible section |
| 19 | Schedule calendar + video preview modal | **Dashboard** | Schedule section |
| 20 | Queue list + metadata edit | **Dashboard** + **Review** | Dashboard: slot drawer / Review: approve metadata |

Каждый существующий контролл имеет чёткое место. Ничего не потеряно.

---

## Что меняется vs текущий UI

| Аспект | Сейчас | Станет |
|--------|--------|--------|
| Create modal | Name + models + prompts + social | Name + workspace only (Q1) |
| Навигация | 5 табов по типу данных | 3 экрана по задачам |
| Settings | Отдельная страница со всем | Pipeline screen + lightweight settings (name only) |
| Variants | Отдельный таб | Pipeline → Input step |
| Templates | Отдельный таб | Pipeline → Video step |
| Publishing config | Publishing tab | Pipeline → Distribution step (Q10) |
| Calendar | Publishing tab | Dashboard screen |
| Generation | Panel + list | Pipeline → Run section (batch + Test per step Q4) |
| Moderation | Список карточек | Focused review one-at-a-time (Q6: first unreviewed) |
| Ratings | Звёзды + комментарий | Удалены (Q5) |
| Slot info при approve | Нет | Видна сразу на Review screen |
| Metadata при approve | Нет | Editable fields на Review screen (Q8) |
| Batch generation | Нет | Pipeline → Run (default mode) |
| Pipeline overview | Нет | Dashboard screen (funnel) |
| Pause publishing | Нет | Dashboard toggle + Distribution toggle (Q7) |
| Smart default screen | Нет (всегда Generate tab) | Зависит от состояния проекта (Q9) |
| Save behavior | Per-form save buttons | Sticky Save bar для всего Configure (Q3) |
| Filmstrip | Нет | Review screen, scroll + filters (Q12) |
| Summary line | Нет | Configure collapsed summary (Q11) |

---

## Scope

| # | Изменение | Новые компоненты |
|---|-----------|------------------|
| 1 | Create modal simplification | Modify `TemplateProjectForm` |
| 2 | 3-screen navigation (Dashboard, Review, Pipeline) | Refactor `TemplateProjectView` |
| 3 | Dashboard: pipeline funnel + calendar + pause toggle | `PipelineFunnel`, reuse `PublishingScheduleView` |
| 4 | Review: focused one-at-a-time + filmstrip + filters | `FocusedReview`, `Filmstrip` |
| 5 | Review: target slot + metadata fields + inline reject/redo | Modify moderation components |
| 6 | Pipeline Configure: step visualization + accordion + Test per step | `PipelineSteps`, `PipelineStep` |
| 7 | Pipeline Configure: Sticky Save bar | `StickySaveBar` |
| 8 | Pipeline Run: batch controls + grouped history (no ratings) | Modify `GenerationPanel`, `GenerationsList` |
| 9 | Smart default screen logic | `TemplateProjectView` |
| 10 | Pipeline stats API | Backend endpoint |
| 11 | Test per step API (Preprocessing/Image/Video) | Backend endpoints for step preview/test |
| 12 | Distribution account check API | Backend endpoint: validate OAuth tokens |
| 13 | Inline OAuth flow in Distribution step | Frontend OAuth integration per platform |
| 14 | Pause publishing (DB field + scheduler logic) | Backend: `is_paused` field in PublishingConfig + APScheduler check |

### Рекомендуемый порядок

**Phase 1 — Navigation + Dashboard:**
3 экрана, pipeline funnel, перенос calendar на Dashboard, pause toggle. Быстрый structural win.

**Phase 2 — Review:**
Focused review, filmstrip с фильтрами, target slot, inline forms, metadata при approve. Главный ежедневный экран.

**Phase 3 — Pipeline:**
Step visualization, accordion settings, Test per step, sticky save bar, batch controls, grouped history. Самый объёмный.

**Phase 4 — Polish:**
Smart default screen, create modal simplification, Settings page cleanup.

---

## Не в scope

- Drag-drop reorder очереди
- Drag-drop видео между слотами
- Multi-level approval workflow
- Analytics / metrics dashboard
- Auto-generation при пустой очереди (T23)
- Keyboard shortcuts для Review (←→ навигация, hotkeys для approve/reject)
