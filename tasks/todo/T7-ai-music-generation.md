---
id: T7
title: AI Music Generation Integration
status: in_progress
priority: high
created: 2026-01-12
updated: 2026-01-12T18:00:00
tags: [audio, ai, music-u, integration, openai, ffmpeg]
depends_on: [T6]
estimate: "3-4 дня"
actual: ""
spec: ""
branch: "feature/T7-ai-music-generation"
related_rca: ""
---

# T7: AI Music Generation Integration

## Scope

**MVP для research/experimentation. Код production-quality.**

## Описание

Добавить генерацию музыки через music-u (Udio) API как альтернативу KLING Sound.
AI анализирует сгенерированный трек и находит лучшие хуки для короткого видео.

## Для пользователя

- Выбор `audio_provider` в проекте: `kling` | `ai_music`
- AI генерирует музыкальный трек на основе сценария
- AI находит лучшие 5-сек хуки в треке
- Preview: video + audio играют синхронно в браузере (без merge)
- User выбирает хук → система делает merge → готовое видео

## Ключевые решения

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | AudioMode enum | Оставить `audio_mode`, добавить `audio_provider` |
| 2 | Связки type↔provider | В коде: `backend/app/core/audio_config.py` |
| 3 | Hook storage | StepHistory.content (как image/video variants) |
| 4 | Hook selection | Каждый hook = отдельный StepHistory record |
| 5 | Error handling | Critical → fail step, 0 hooks → fallback весь трек |
| 6 | Preview | Pre-trim все хуки, video+audio sync в браузере |
| 7 | Merge timing | Сразу после approve хука |
| 8 | OPENAI_API_KEY | Optional, ai_music disabled если нет ключа |
| 9 | **Архитектура провайдеров** | **Composition pattern: providers по capability + shared core services** |
| 10 | **Merge location** | **approve endpoint в api/workflow.py** |
| 11 | **Temp files** | **data/temp/ + cleanup при старте (files older than 24h)** |
| 12 | **Audio file serving** | **Добавить `audio` в /api/files, хранить в data/media/audio/** |
| 13 | **Temp file naming** | **{video_id}_hook_{start}_{end}.mp3** |
| 14 | **Provider signature** | **`generate(video) -> Dict` как image.py/video.py (без AudioContext)** |

## Технический стек

| Компонент | Решение |
|-----------|---------|
| Music Generation | music-u (PiAPI) |
| Audio Analysis | GPT-4o-audio-preview (OpenAI direct) |
| Audio Processing | FFmpeg (trim, fade, merge) |

## Архитектура

### Provider Pattern (Composition)

```
providers/
├── factory.py              ← get_video_provider(), get_audio_provider()
├── protocols/
│   ├── video.py            ← VideoProviderProtocol
│   └── audio.py            ← AudioProviderProtocol
├── video/
│   └── kling.py            ← KlingVideoProvider (existing)
├── audio/
│   ├── kling.py            ← KlingAudioProvider (existing logic)
│   └── ai_music.py         ← AiMusicProvider (NEW) - компонует core services
└── image/
    └── kling.py            ← (existing)

core/
├── music_generator.py      ← music-u client (PiAPI)
├── hook_analyzer.py        ← GPT-4o-audio (OpenAI direct)
└── media_processor.py      ← FFmpeg operations (shared)
```

### AiMusicProvider Flow

```
1. video (scenario_data, project.platforms, project.duration)
        ↓
2. GPT-4o (PiAPI) → generate music prompt
   "80s synthpop, energetic, romantic, Miami summer vibes"
        ↓
3. music-u API (PiAPI) → full track (30-60 сек)
        ↓
4. GPT-4o-audio-preview (OpenAI direct) → найти хуки
   [возвращает JSON с timestamps лучших сегментов]
        ↓
5. FFmpeg → trim ALL hooks (5 сек) + fade in/out 0.5s
   [сохраняем в data/media/audio/, создаём 4 StepHistory записи]
        ↓
6. Frontend: video + audio sync preview (no merge yet)
        ↓
7. User selects hook → select endpoint
        ↓
8. FFmpeg → merge video + trimmed audio
   [сохраняем в data/media/videos/]
        ↓
9. video.video_with_audio_url = /api/files/videos/{id}_final.mp4
```

### Workflow Integration

```python
# workflow/steps/audio.py
from app.providers.factory import get_audio_provider

async def generate(video) -> Dict[str, Any]:
    """Same signature as image.py and video.py - uses Video directly."""
    provider = get_audio_provider(video.project.audio_provider or "kling")
    return await provider.generate(video)
```

## PoC Results (validated)

| Этап | Статус | Notes |
|------|--------|-------|
| GPT-4o audio анализ хуков | ✅ | Находит 3-6 хуков с timestamps |
| FFmpeg trim сегмента | ✅ | Точная нарезка по секундам |
| FFmpeg fade in/out | ✅ | 0.5s fade, двухшаговый процесс |
| FFmpeg merge video+audio | ✅ | -shortest для sync |

## Legal Disclaimer

⚠️ **AI-музыка имеет юридические риски:**
- Suno/Udio под судебными исками от major labels
- Output может содержать элементы copyrighted материала
- Используется только для research/experimentation

---

## Files to Modify

### Provider Infrastructure (NEW)

| File | Type | Changes |
|------|------|---------|
| `backend/app/providers/__init__.py` | New | Package init |
| `backend/app/providers/factory.py` | New | get_video_provider(), get_audio_provider() |
| `backend/app/providers/protocols/video.py` | New | VideoProviderProtocol |
| `backend/app/providers/protocols/audio.py` | New | AudioProviderProtocol |
| `backend/app/providers/audio/kling.py` | New | KlingAudioProvider (extract from existing) |
| `backend/app/providers/audio/ai_music.py` | New | AiMusicProvider (composition) |

### Core Services (NEW)

| File | Type | Changes |
|------|------|---------|
| `backend/app/core/music_generator.py` | New | music-u client (PiAPI) |
| `backend/app/core/hook_analyzer.py` | New | GPT-4o-audio analysis (OpenAI) |
| `backend/app/core/media_processor.py` | New | FFmpeg: trim, fade, merge, duration |

### Config & Models

| File | Type | Changes |
|------|------|---------|
| `backend/app/core/audio_config.py` | New | AudioType, AudioProvider, связки type↔provider |
| `backend/app/core/config.py` | Modify | OPENAI_API_KEY, OPENAI_AUDIO_MODEL, TEMP_DIR |
| `backend/app/models/project.py` | Modify | add audio_provider field |
| `backend/app/schemas/project.py` | Modify | add audio_provider to schema |
| `alembic/versions/xxx_add_audio_provider.py` | New | migration |

### Existing Services (Modify)

| File | Type | Changes |
|------|------|---------|
| `backend/app/services/piapi_client.py` | Modify | create_music_task(), generate_music() |
| `backend/app/services/workflow/steps/audio.py` | Modify | use provider factory |
| `backend/app/services/prompts/music_prompt.py` | New | GPT промпт для музыки |

### API & Dependencies

| File | Type | Changes |
|------|------|---------|
| `backend/app/api/workflow.py` | Modify | merge в approve endpoint |
| `backend/app/api/config.py` | New | GET /api/config/audio-options router |
| `backend/app/api/files.py` | Modify | add audio type + mp3 MIME |
| `backend/app/main.py` | Modify | startup: FFmpeg check + temp cleanup |
| `backend/requirements.txt` | Modify | add openai>=1.10.0 |

### Frontend

| File | Type | Changes |
|------|------|---------|
| `frontend/src/components/ProjectForm.tsx` | Modify | audio_provider select |
| `frontend/src/components/audio/HookSelector.tsx` | New | preview video+audio, select hook |
| `frontend/src/types/index.ts` | Modify | AudioProvider type |

---

## Acceptance Criteria

### Provider Architecture
- [ ] `providers/factory.py` — get_audio_provider(), get_video_provider()
- [ ] `providers/protocols/audio.py` — AudioProviderProtocol
- [ ] `providers/audio/kling.py` — KlingAudioProvider
- [ ] `providers/audio/ai_music.py` — AiMusicProvider (composition)

### Core Services
- [ ] `core/media_processor.py` — FFmpeg operations (shared)
- [ ] `core/music_generator.py` — music-u client
- [ ] `core/hook_analyzer.py` — GPT-4o-audio analysis
- [ ] `core/audio_config.py` — type↔provider связки

### Integration
- [ ] `workflow/steps/audio.py` — uses provider factory
- [ ] `api/workflow.py` — merge в approve для ai_music
- [ ] `piapi_client.py` — music-u methods

### Config & DB
- [ ] `OPENAI_API_KEY` optional (disable ai_music если нет)
- [ ] DB migration для audio_provider field

### Frontend
- [ ] ProjectForm: audio_provider select + legal disclaimer
- [ ] HookSelector: video+audio sync preview

### Tests
- [ ] `pytest` проходит
- [ ] `npm run build` успешно

---

## Чек-лист

### T7.1: Provider Infrastructure

- [ ] Создать `backend/app/providers/` package
  - [ ] `__init__.py`
  - [ ] `factory.py`:
    ```python
    def get_audio_provider(name: str) -> AudioProviderProtocol:
        providers = {"kling": KlingAudioProvider, "ai_music": AiMusicProvider}
        return providers[name]()

    def get_video_provider(name: str) -> VideoProviderProtocol:
        providers = {"kling": KlingVideoProvider}
        return providers[name]()
    ```
- [ ] Создать `backend/app/providers/protocols/`
  - [ ] `audio.py` — `AudioProviderProtocol` (Protocol class)
  - [ ] `video.py` — `VideoProviderProtocol` (Protocol class)

### T7.2: Audio Config

- [ ] Создать `backend/app/core/audio_config.py`
  - [ ] `AudioType = Literal["none", "scene", "music", "voiceover", "auto"]`
  - [ ] `AudioProvider = Literal["kling", "ai_music"]`
  - [ ] `AUDIO_TYPE_PROVIDERS: dict` — какие провайдеры для каких типов
  - [ ] `DEFAULT_PROVIDER: dict` — default провайдер для типа
  - [ ] `is_valid_combination(audio_type, provider) -> bool`
  - [ ] `is_ai_music_available() -> bool` — проверка OPENAI_API_KEY

### T7.3: Config Updates

- [ ] Обновить `backend/app/core/config.py`
  - [ ] `OPENAI_API_KEY: str = ""` (optional)
  - [ ] `OPENAI_AUDIO_MODEL: str = "gpt-4o-audio-preview"`
  - [ ] `TEMP_DIR: str = "data/temp"`

### T7.4: Database Migration

- [ ] Обновить `backend/app/models/project.py`
  - [ ] Добавить `audio_provider: str` field (nullable, default None)
- [ ] Обновить `backend/app/schemas/project.py`
  - [ ] Добавить `audio_provider: Optional[str]`
  - [ ] Validator: проверка валидности комбинации
- [ ] Создать alembic migration
  - [ ] `alembic revision --autogenerate -m "add audio_provider to project"`
  - [ ] В upgrade: `UPDATE projects SET audio_provider = 'kling' WHERE audio_mode != 'none'`

### T7.5: Core — Media Processor (shared)

- [ ] Создать `backend/app/core/media_processor.py`
  - [ ] `async def download_file(url, dest_path) -> str`
  - [ ] `async def get_audio_duration(audio_path) -> float` (FFprobe)
  - [ ] `async def trim_audio(audio_path, start, end, fade_in=0.5, fade_out=0.5) -> str`
    - [ ] Two-step FFmpeg (trim then fade) для качества
    - [ ] Использовать asyncio.create_subprocess_exec (не блокировать)
  - [ ] `async def merge_video_audio(video_path, audio_path) -> str`
  - [ ] `async def check_ffmpeg_available() -> bool`
  - [ ] Cleanup temp files with context manager

### T7.6: PiAPI Client — Music Methods

- [ ] Обновить `backend/app/services/piapi_client.py`
  - [ ] `async def create_music_task(prompt, lyrics_type="instrumental", seed=-1) -> str`
  - [ ] `async def wait_for_music(task_id, timeout=300) -> str`
  - [ ] `async def generate_music(prompt, **kwargs) -> str` (high-level)

### T7.7: Core — Music Generator

- [ ] Создать `backend/app/core/music_generator.py`
  - [ ] `async def generate_prompt(video) -> str` (GPT via PiAPI)
    - [ ] Использует video.scenario_data, video.project.platforms, video.project.duration
  - [ ] `async def generate_track(prompt, lyrics_type="instrumental") -> str` (music-u via PiAPI)
- [ ] Создать `backend/app/services/prompts/music_prompt.py`
  - [ ] GPT промпт учитывает scenario, mood, platforms

### T7.8: Core — Hook Analyzer

- [ ] Создать `backend/app/core/hook_analyzer.py`
  - [ ] `__init__`: инициализация OpenAI client (settings.OPENAI_API_KEY)
  - [ ] `async def find_hooks(audio_path, video, num_hooks=4) -> list[Hook]`
    - [ ] Использует video.scenario_data для контекста (описание сцены, настроение)
  - [ ] Hook dataclass: start, end, duration, reason, energy, type
  - [ ] Error handling: return single "full track" hook если 0 найдено

### T7.9: Provider — Kling Audio

- [ ] Создать `backend/app/providers/audio/kling.py`
  - [ ] Extract existing KLING audio logic from workflow
  - [ ] Implement `AudioProviderProtocol`
  - [ ] `async def generate(self, video) -> Dict[str, Any]`
    - [ ] Вызывает kling_service.add_audio_to_video()

### T7.10: Provider — AI Music

- [ ] Создать `backend/app/providers/audio/ai_music.py`
  - [ ] Implement `AudioProviderProtocol`
  - [ ] Compose: MusicGenerator + HookAnalyzer + MediaProcessor
  - [ ] `async def generate(self, video) -> Dict[str, Any]`:
    ```python
    async def generate(self, video) -> Dict[str, Any]:
        # 1. Generate music prompt from scenario
        prompt = await self.music_gen.generate_prompt(video)
        # 2. Generate full track via music-u
        track_url = await self.music_gen.generate_track(prompt)
        # 3. Download to temp
        track_path = await self.processor.download_file(track_url, f"data/temp/{video.id}_full.mp3")
        # 4. Find hooks
        hooks = await self.analyzer.find_hooks(track_path, video)
        # 5. Trim all hooks and save to data/media/audio/
        variants = []
        for hook in hooks:
            filename = f"{video.id}_hook_{int(hook.start)}_{int(hook.end)}.mp3"
            trimmed_path = await self.processor.trim_audio(
                track_path, hook.start, hook.end,
                output_path=f"data/media/audio/{filename}"
            )
            variants.append({
                "hook": asdict(hook),
                "preview_url": f"/api/files/audio/{filename}",
                "full_track_url": track_url,
                "music_prompt": prompt,
            })
        return {"variants": variants, "full_track_url": track_url}
    ```
  - [ ] Error handling: music API fail → raise, 0 hooks → fallback full track

### T7.11: Workflow Integration

- [ ] Обновить `backend/app/services/workflow/steps/audio.py`
  - [ ] Use provider factory:
    ```python
    from app.providers.factory import get_audio_provider

    async def generate(video) -> Dict[str, Any]:
        provider = get_audio_provider(video.project.audio_provider or "kling")
        return await provider.generate(video)
    ```
- [ ] Обновить approve endpoint в `backend/app/api/workflow.py`
  - [ ] После approve audio варианта для ai_music — выполнить merge:
    ```python
    # В select endpoint после сохранения выбранного варианта
    if step == "audio" and video.project.audio_provider == "ai_music":
        from app.core.media_processor import MediaProcessor
        processor = MediaProcessor()

        # Get paths
        selected_content = selected_variant.content
        audio_url = selected_content["preview_url"]  # /api/files/audio/...
        audio_path = f"data/media/audio/{audio_url.split('/')[-1]}"

        # Download video to temp (it's external URL)
        video_path = await processor.download_file(
            video.video_url,
            f"data/temp/{video.id}_video.mp4"
        )

        # Merge
        merged_filename = f"{video.id}_final.mp4"
        merged_path = await processor.merge_video_audio(
            video_path, audio_path,
            output_path=f"data/media/videos/{merged_filename}"
        )

        # Update video
        video.video_with_audio_url = f"/api/files/videos/{merged_filename}"
        video.audio_url = audio_url
        db.commit()

        # Cleanup temp video
        os.remove(video_path)
    ```

### T7.12: API Endpoint — Audio Options

- [ ] Создать `backend/app/api/config.py` (новый router)
- [ ] Добавить `GET /api/config/audio-options`
  - [ ] Response schema:
    ```json
    {
      "types": ["none", "scene", "music", "voiceover", "auto"],
      "providers": {
        "music": ["kling", "ai_music"],
        "scene": ["kling"],
        "voiceover": ["kling"],
        "auto": ["kling", "ai_music"]
      },
      "defaults": {
        "music": "kling",
        "scene": "kling",
        "voiceover": "kling",
        "auto": "kling"
      },
      "ai_music_available": true
    }
    ```
  - [ ] `ai_music_available` = `is_ai_music_available()` из audio_config
- [ ] Зарегистрировать router в `main.py`

### T7.13: Frontend — ProjectForm

- [ ] Обновить `frontend/src/components/ProjectForm.tsx`
  - [ ] Добавить `audio_provider` select (показывать если audio_mode = music)
  - [ ] Options из `/api/config/audio-options`
  - [ ] Legal disclaimer при выборе ai_music:
    ```tsx
    <Alert severity="warning">
      ⚠️ AI-музыка экспериментальная. Только для research/testing.
    </Alert>
    ```
- [ ] Обновить `frontend/src/types/index.ts`
  - [ ] `AudioProvider = "kling" | "ai_music"`
  - [ ] Добавить в Project type

### T7.14: Frontend — HookSelector

- [ ] Создать `frontend/src/components/audio/HookSelector.tsx`
  - [ ] Props: hooks[], videoUrl, onSelect
  - [ ] Video player (muted)
  - [ ] Hook list с metadata (timestamps, reason, energy)
  - [ ] Preview button: play video + audio синхронно
  - [ ] Select button: call onSelect(hookId)
- [ ] Интегрировать в существующий variants UI

### T7.15: Files API — Audio Support

- [ ] Обновить `backend/app/api/files.py`
  - [ ] Добавить `"audio"` в `ALLOWED_TYPES`
  - [ ] Добавить `"mp3": "audio/mpeg"` в `MIME_TYPES`
- [ ] Создать директорию `data/media/audio/` (или auto-create)

### T7.16: Dependencies & Infrastructure

- [ ] Обновить `backend/requirements.txt`
  - [ ] `openai>=1.10.0`
- [ ] Auto-create directories в media_processor:
  - [ ] `data/temp/`
  - [ ] `data/media/audio/`
- [x] FFmpeg установлен (macOS) ✅
- [ ] Startup checks в `backend/app/main.py`:
  ```python
  @app.on_event("startup")
  async def startup_checks():
      from app.core.media_processor import MediaProcessor
      from app.core.audio_config import is_ai_music_available

      # Check FFmpeg
      processor = MediaProcessor()
      if not await processor.check_ffmpeg_available():
          logger.warning("FFmpeg not found - ai_music provider will fail")

      # Cleanup old temp files (older than 24h)
      await processor.cleanup_temp_files(max_age_hours=24)

      # Log ai_music status
      if is_ai_music_available():
          logger.info("ai_music provider: enabled")
      else:
          logger.info("ai_music provider: disabled (OPENAI_API_KEY not set)")
  ```

### T7.17: Testing

- [ ] `cd backend && venv/bin/pytest`
- [ ] `cd frontend && npm run build`
- [ ] Manual test: full flow с ai_music

---

## API Reference

### music-u (PiAPI)

```json
POST https://api.piapi.ai/api/v1/task
{
    "model": "music-u",
    "task_type": "generate_music",
    "input": {
        "gpt_description_prompt": "80s synthpop, energetic, romantic",
        "lyrics_type": "instrumental",
        "seed": -1
    }
}
```

### GPT-4o Audio (OpenAI direct)

```python
import openai
import base64

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

with open("track.mp3", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="gpt-4o-audio-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "mp3"}},
            {"type": "text", "text": "Find hooks..."}
        ]
    }]
)
```

### FFmpeg Commands

```bash
# Trim + fade (two-step for quality)
ffmpeg -i track.mp3 -ss 73.0 -t 5.0 -vn -b:a 192k temp.mp3
ffmpeg -i temp.mp3 -af "afade=t=in:d=0.5,afade=t=out:st=4.5:d=0.5" -b:a 192k hook.mp3

# Merge video + audio
ffmpeg -i video.mp4 -i hook.mp3 -c:v copy -c:a aac -shortest output.mp4
```

---

## Data Models

### Hook (dataclass)

```python
@dataclass
class Hook:
    start: float        # seconds
    end: float          # seconds
    duration: float     # end - start
    reason: str         # why this is a good hook
    energy: str         # low/medium/high
    type: str           # chorus/drop/bridge/etc
    preview_url: str    # /api/files/audio/{video_id}_hook_{start}_{end}.mp3
```

### StepHistory.content for audio (ai_music)

```json
{
    "hook": {
        "start": 73.0,
        "end": 78.0,
        "duration": 5.0,
        "reason": "Bright chorus with instant impact",
        "energy": "high",
        "type": "chorus"
    },
    "preview_url": "/api/files/audio/v123_hook_73_78.mp3",
    "full_track_url": "https://...",
    "music_prompt": "80s synthpop, energetic..."
}
```

---

## Error Handling

| Error | Behavior |
|-------|----------|
| music-u API fail | Fail step, log error, user can retry or switch to kling |
| OpenAI audio fail | Fail step, log error |
| FFmpeg fail | Fail step, log error |
| 0 hooks found | Fallback: use full track as single "hook" (0 to duration) |
| OPENAI_API_KEY missing | ai_music disabled, user can only use kling |

---

## Notes

- music-u API доступен через PiAPI
- GPT-4o-audio-preview требует отдельный OpenAI API key
- FFmpeg установлен локально, нужно на сервере
- Pre-trim все хуки для instant preview
- Merge только после approve (не раньше)
- Temp files cleanup после операций

## Related

- Plan: `/Users/gmartirosov/.claude/plans/calm-tinkering-metcalfe.md`
- PoC files: `~/Downloads/hooks/`
