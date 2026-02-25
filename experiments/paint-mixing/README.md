# Эксперимент: Paint Mixing

Первый полный прогон пайплайна Agent Producer — от идеи до опубликованного ролика. Ручная симуляция для фиксации алгоритма.

## Метрики

| Video | Format | Duration | Model | Views | Retention | APV | Likes | Comments | Subs | Period |
|-------|--------|----------|-------|-------|-----------|-----|-------|----------|------|--------|
| v1 | Reverse | 8s | Veo 3.1 | 200 | 35% | — | 3 | 0 | 0 | 1.5h |
| v1 | | | | 1.9K | 47% | — | 9 | 1 | 1 | 17h |
| v2 | Hooked (cut 2.5s) | 10s | Minimax Hailuo-02 | 1.7K | 37.2% | — | 7 | 1 | 0 | 11h |
| v3a | Hooked (cut 16s) + twist | 18s | Minimax Hailuo-02 ×3 | 7 | 17% | — | 0 | 0 | 0 | 0.5h (unlisted) |
| v3b | Straight | 18s | Minimax Hailuo-02 ×3 | 76 | 37% | — | — | — | — | 24min |
| v3b | | | | 591 | 56.7% | 86.4% | 10 | — | 1 | 3h |

## Результат

Опубликован YouTube Short (реверс-версия): uniform цвет → 3 отдельных блоба. CTA "guess color in comments?".

## Пайплайн (что прошли)

```
Research → Image Prompts → Generate Start Frame → Generate End Frame → Video (10 моделей) → Music (Lyria2) → Hook Extraction → Assemble → CTA Overlay → Reverse → Publish
```

## Статус

| Этап | Статус | Артефакт |
|------|--------|----------|
| Research brief | done | [research-brief.md](research-brief.md) |
| Алгоритм ресерча | done | [research-algorithm.md](research-algorithm.md) |
| Image промпты | done | [prompts/image/prompts.md](prompts/image/prompts.md) |
| Video промпты | done | промпт в скриптах |
| Start frame (A2) | done | 3 blobs: teal, magenta, yellow |
| End frame | done | uniform teal-green (Nano Banana Pro /edit) |
| Video comparison (10 моделей) | done | [results/VIDEO_COMPARISON.md](results/VIDEO_COMPARISON.md) |
| Music (Lyria2) | done | results/music_full.wav, music_hook_15s.wav |
| Final assembly | done | results/final_with_cta.mp4 |
| Reverse version | done | results/final_with_cta_reverse_v2.mp4 |
| YouTube publish | done | реверс-версия |

## Ключевые находки

### Start+End Frame — критически важно

Без end frame видео заканчивается "на полпути" — краски не домешаны. Start+end frame решает проблему: модель знает куда вести визуал.

**Модели с поддержкой start+end frame:**

| Модель | $/сек | Макс длина | Параметры end frame |
|--------|-------|-----------|---------------------|
| Minimax Hailuo-02 | $0.05 | 10s | `end_image_url` |
| PixVerse v5.5 Transition | ~$0.12 | 10s | `end_image_url` |
| Kling v3 Standard | $0.168 | 15s | `end_image_url` |
| Kling O3 Standard | $0.168 | 15s | `end_image_url` |
| Veo 3.1 | $0.20 | 8s | `first_frame_url` + `last_frame_url` (отдельный endpoint!) |
| Kling v3 Pro | $0.224 | 10s | `end_image_url` |

**Без поддержки:** Grok Imagine Video, Sora 2 (не проверено).

**Veo 3.1 — отдельный endpoint:** `fal-ai/veo3.1/first-last-frame-to-video` (не `/image-to-video`).

### End Frame через Image Edit

Nano Banana Pro `/edit` отлично работает для генерации end frame из start frame. Ключ — максимально конкретный промпт:
- "perfectly uniform flat color" (не "mixed")
- "no swirls, no streaks, no marble pattern"
- "Flat smooth paint surface like fresh house paint"
- Явно указать что НЕ менять: "same can, same hand position, same table, same lighting"

Первая попытка (с "marbled swirl") дала полосатый результат. Только "uniform flat color" + "no swirls" дало чистый цвет.

### Video Model Comparison

Протестировано 10 генераций на 7 моделях. Победитель для этого концепта — **Veo 3.1**:
- Лучшее качество motion для жидкостей
- 8с максимум — достаточно для short
- $1.60 за генерацию
- Start+end frame гарантирует полный цикл

Полная таблица: [results/VIDEO_COMPARISON.md](results/VIDEO_COMPARISON.md)

### Music Pipeline

1. Lyria2 генерит ~30с трек по промпту
2. HookAnalyzer (FFmpeg RMS energy) находит лучший сегмент
3. FFmpeg обрезает с fade-in/fade-out
4. FFmpeg мержит видео + аудио

Для ambient музыки HookAnalyzer работает, но разница между сегментами минимальная — энергия ровная.

**Промпт для ambient:** "Slow ambient lo-fi beat, soft padded synths, gentle vinyl crackle. Hypnotic and satisfying. Deep bass hum with minimal percussion. Dreamy, meditative mood. No vocals. 80 BPM."

### Assembly Pipeline

```
FFmpeg:
1. Download video (curl/urllib)
2. Trim audio to video length + fade-in/out
3. Merge: -c:v libx264 -c:a aac -b:a 256k -ar 44100 (НЕ -c:v copy — были проблемы со звуком)
4. CTA overlay: drawtext filter (white, borderw=3 black, top center)
5. Reverse: -vf "reverse" (видео), audio — оставить прямым
```

**Важно:** `ffmpeg -c:v copy -c:a aac` давал файл без звука в некоторых плеерах. Полная перекодировка (`-c:v libx264`) решила проблему.

### YouTube Meta для Paint Mixing

**Паттерны топовых каналов (Fritz Proctor, Smashing Pencils):**
- Title формулы: `Color + Color = ?`, `Guess the final color`, `What colors made this?`
- 3-5 хештегов: `#shorts #satisfying #paintmixing #asmr #colormixing`
- Описание: 1-2 строки + CTA + хештеги
- CTA в оверлее совпадает с title/description

**Для реверса (наш формат):** зритель видит готовый цвет, угадывает ингредиенты → "What colors made this?" / "guess the colors"

### Реверс как контент-приём

Один ролик → два формата:
1. **Forward:** 3 блоба → uniform цвет ("guess the final color")
2. **Reverse video + forward audio:** uniform → 3 блоба ("what colors made this?")

Реверс визуально работает отлично для paint mixing — "unmixing" эффект залипательный.

## Стоимость эксперимента

| Статья | Сумма |
|--------|-------|
| Image генерации (~6 штук, Nano Banana Pro) | ~$0.30 |
| End frame edit (2 попытки) | ~$0.10 |
| Video генерации (10 штук, разные модели) | ~$13.50 |
| Music (Lyria2, 2 генерации) | ~$0.20 |
| **Итого** | **~$14.10** |

Из них продакшен-стоимость одного ролика (если бы сразу знали модель): image $0.05 + end frame edit $0.05 + Veo video $1.60 + music $0.10 = **~$1.80/ролик**.

## Файлы

```
experiments/paint-mixing/
├── README.md                          # этот файл
├── research-brief.md                  # финальный бриф (score 85)
├── research-algorithm.md              # алгоритм ресерча
├── VIDEO_COMPARISON.md                # сводная таблица всех видео
└── v1/                                # первая итерация (reverse, 8с, Veo 3.1)
    ├── prompts/
    │   └── image/prompts.md           # image промпты (score 87)
    ├── scripts/
    │   ├── generate_images.py         # генерация start frame
    │   ├── generate_end_frame.py      # генерация end frame (edit)
    │   ├── generate_video.py          # video: Kling 2.6 Pro
    │   ├── generate_video_startend.py # video: Kling v3 start+end
    │   ├── generate_video_minimax.py  # video: Minimax Hailuo-02
    │   ├── generate_video_pixverse.py # video: PixVerse v5.5 Transition
    │   ├── generate_video_grok.py     # video: Grok Imagine Video
    │   ├── generate_video_veo.py      # video: Veo 3.1 start+end
    │   ├── generate_video_klingo3.py  # video: Kling O3 start+end
    │   ├── generate_music.py          # music: Lyria2 + HookAnalyzer
    │   └── assemble_final.py          # assembly: video + audio + CTA
    └── results/
        ├── music_full.wav             # полный трек Lyria2
        ├── music_hook_15s.wav         # лучший 15с хук
        ├── final_veo_with_music_v2.mp4    # финал: forward
        ├── final_with_cta.mp4             # финал: forward + CTA
        ├── final_with_cta_reverse.mp4     # финал: reverse (всё)
        ├── final_with_cta_reverse_v2.mp4  # финал: reverse video + forward audio ← PUBLISHED
        └── *.json                         # метадата генераций
```
