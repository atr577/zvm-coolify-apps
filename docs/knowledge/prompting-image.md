# Image Model Prompting

## Core Rule
Subject first. AI image models weigh early tokens more heavily — what you write first gets the most attention.

## Prompt Structure (in order)

1. **Subject** — main object/character + visual details (material, color, texture)
2. **Action/State** — what's physically happening, pose
3. **Environment** — background, setting, location
4. **Camera** — angle, distance, depth of field
5. **Lighting** — source, direction, color temperature
6. **Composition** — framing for aspect ratio, placement
7. **Style** — 2-3 technical keywords (photorealistic, cinematic, etc)
8. **Constraints** — "No text, no watermarks, no logos"

## Rules

1. **Every word = something visible.** If you can't point to it in the image — delete it.
2. **50-150 words.** Shorter = sharper. Longer = model ignores late tokens.
3. **No prose.** "A strikingly powerful press looms dramatically" = bad. "Industrial hydraulic press, steel surface" = good.
4. **No narrative.** "Capturing the viewer's attention" = invisible, useless.
5. **No metaphors.** "Like colored stars" — model will try to draw stars.
6. **Specific > vague.** "Warm golden sunset light from the left at 45 degrees" > "nice lighting".
7. **"Top-down flat lay" for close-up overhead.** "Bird's eye view" = distant wide shot. "Top-down flat lay" = close-up straight down 90°, standard product photography term. Confirmed in Nano Banana Pro prompt guide.

## Realistic People (proven pattern: "девушки и машины")

### Pipeline
Structured JSON preprocessing → assembled image prompt.

LLM получает короткое описание (город, авто, модель, одежда) и генерирует детальный JSON:
- header: concept_title, nationality, car, location
- model: profile (nationality, age, ethnicity), face (expression, gaze), hair, skin, makeup, pose, outfit
- subject: car type, exterior/interior color, state, restrictions
- composition: setting, lighting, camera (framing, angle, lens, distance), focus, layout
- constraints: no text, no logos, no plates

Затем image_prompt_template собирает JSON в один промпт по порядку:
CONCEPT → LOCATION → CAR → MODEL → OUTFIT → CINEMATIC → FOCUS → LAYOUT → RESTRICTIONS

### Key Details
- Camera: medium/medium-close, side 3/4 ~45°, eye-level, 50-85mm look
- DOF: shallow, background soft but readable
- Constraints: no readable license plates, no logos, background people/cars far/mid only
- Tone: cinematic fashion-editorial, ultra-premium, no vulgarity

### Example Output
```
Young confident Italian woman, olive skin, dark wavy hair past shoulders, subtle smokey eye makeup,
sitting in passenger seat of matte black Porsche 911, door open toward camera.
She wears a fitted ivory blazer over black silk camisole, relaxed confident expression, gaze toward camera.
Rome, Piazza Navona at twilight, warm street lamps reflecting on wet cobblestones.
Medium-close shot, side 3/4 angle, eye-level, 50-85mm lens look.
Golden hour backlighting with warm fill from street lamps, shallow depth of field.
Vertical 9:16, model in upper third, car occupies 40% of frame.
Ultra-premium cinematic fashion-editorial photography.
No text, no watermarks, no logos, no readable license plates.
```

## Abstract/Ink (proven pattern: "чернила в силуэты")

### Pipeline
Simple template with placeholders — no LLM preprocessing needed.

Variants provide only `color` and `subject`. Template is fixed:
```
In a studio setting with a black background, capture a close-up shot of swirling {color} ink
as it forms the silhouette of a {subject}. Front-facing camera angle, straightforward compelling view.
Subtle diffused lighting, softening shadows, drawing attention to the emerging {subject}'s outline.
The moment focuses on the initial swirl creating the {subject}'s nose and ears.
Vertical 9:16. Style: photorealistic. Quality: ultra-detailed, high-resolution, 8K.
No text, watermarks, or logos.
```

### Key Details
- Background: always pure black (contrast is everything)
- Lighting: diffused, subtle — no hard shadows
- Camera: front-facing, close-up, static
- Subject: described as silhouette forming, not completed
- Performance insight: контрастные яркие цвета (green, teal, magenta) work best; warm/skin tones underperform

## Limitations of Current Knowledge

Все production примеры — **один кадр для одной сцены.** Нет проверенного опыта с:
- Генерацией серии связанных кадров (storyboard)
- img2img для continuity между сценами
- Генерацией пар картинок с контролируемыми отличиями ("найди отличия")
- Генерацией текстовых оверлеев внутри изображения (а не поверх видео)

TODO: протестировать эти сценарии, обновить этот файл.

## Discover Workflow (exploration → refinement)

### Round 1 — Wide (10 prompts)
Максимальное разнообразие: vary camera, lighting, subject treatment, environment.
Each prompt = standalone first frame for a viral short video.

### Round 1 — Refined (4 prompts)
Same scene, different photographer. Preserve subject/environment/style. Vary only camera angle, lighting direction, distance, detail focus.

### Round 2+ — Narrow (10 prompts)
Analyze selected vs rejected → 70% match liked patterns, 30% explore nearby.
User feedback overrides pattern analysis.

## Models on fal.ai

| Model | Best for |
|-------|----------|
| **Nano Banana Pro** | Реализм, people, img2img edit |
| **Flux Kontext Pro** | Image-to-image editing, local edits |
| **Recraft V3** | Text rendering, vector art, style consistency |
| **Seedream V4** | Budget, mass generation |
| **Ideogram v3** | Text rendering 90%+ accuracy |

---
Created: 2026-02-17
