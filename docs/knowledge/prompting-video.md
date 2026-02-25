# Video Model Prompting (i2v)

## Kling (v2, v3)

### Core Rule
i2v prompt = ONLY motion instructions. Model already sees the image — never redescribe what's in it.

### Structure
One paragraph: what moves + how + camera + pacing. No sections, no labels.

### Good Prompt (simple)
```
Ink clouds slowly drift inward toward center of frame,
tendrils curl and merge into a dense cluster. Camera static.
Smooth, fluid motion throughout.
```

### Bad Prompt
```
Subject: abstract colored ink clouds on black background
Motion: ink tendrils pull together toward center, swirling and condensing into the shape of a centaur archer
Camera: static
Speed: medium
Details: purple and teal ink strands weave together
```
Why bad: redescribes what's already in the image (subject, colors), tries complex morph (ink → centaur) in one shot.

### Rules

1. **One action per 3s** — complex morphs (A dissolves → reforms as B) fail. One simple movement per clip.
2. **Motion endpoints** — specify start and end state: "starts spread out, ends clustered in center". Open-ended motion ("swirling") causes hangs or loops.
3. **No scene description** — don't describe subject, colors, background. Only describe MOVEMENT.
4. **Camera always explicit** — "camera static", "slow tracking right", "gentle push-in". Missing camera = static or random.
5. **Pacing words** — "slowly", "gradually", "quickly" control speed. Without them timing is unpredictable.
6. **No contradictions** — "slow motion" + "fast" in same prompt = garbage.
7. **No simultaneous complex transforms** — "360 rotation + zoom + pan" = warped geometry. One camera move at a time.
8. **Consistent style vocabulary** — don't mix "golden hour" with "studio lighting".
9. **"Maintains exact appearance throughout"** — add this if object changes shape mid-video (morphing problem).

### Common Failures
- Too many elements = overload, nothing moves well
- Missing camera = static or unpredictable
- Vague spatial language ("somewhere", "around") = distortion
- Open-ended motion without endpoint = 99% hangs
- Multiple simultaneous camera transforms = warped geometry

### Duration Guidance
- 3s: one simple action (drift, rotate, fade)
- 5s: one action with buildup (slow start → peak)
- 9-10s: two sequential actions possible (A then B), but simpler is better

## Limitations of Current Knowledge

Все production примеры ниже — **одна сцена, один непрерывный шот, одна камера.** Нет проверенного опыта с:
- Multi-shot (Kling O3 — до 6 шотов в одном запросе)
- Склейкой нескольких видео (concat)
- Chained generation (last frame → next video)
- img2img между сценами для continuity
- Сложными трансформациями (A → B морфинг)

Единственный эксперимент с chained video (`experiments/chained_video.py`) дал плохой результат — стыки видны, качество контента низкое.

TODO: протестировать multi-shot и chain, обновить этот файл.

## Production Examples

### Realistic People — "девушки и машины" (Kling v3 Standard, 8s)

Labeled format with per-second timeline:

```
Photorealistic cinematic image-to-video using the reference image as the exact look.
Single continuous shot, 10 seconds, smooth natural motion, keep the model's identity/outfit/car
perfectly consistent. Vertical 9:16, 24fps, no cuts.

Action (10s timeline):
  * 0.0–2.5s: She elegantly steps out of the car (controlled, graceful),
    straightens her posture with a subtle smile.
  * 2.5–3.5s: She closes the door gently (no slam), hand leaves the handle naturally.
  * 3.5–7.0s: She walks toward the front/hood along the side of the car
    (3–4 confident, model-like steps), calm expression.
  * 7.0–8.5s: She reaches the hood area and leans back with her hips lightly
    resting against the hood edge (clean, classy pose), hands relaxed.
  * 8.5–10.0s: She tilts her head and gaze upward, looking dreamy and thoughtful,
    holding the pose for the final beat.

Camera / follow / focus: Gimbal-stabilized. Camera starts medium-wide and tracks smoothly
alongside her as she walks, then settles into a slightly wider framing at the hood.
Subtle slow dolly-out to keep her fully in frame. Focus locked on her face/upper body
with cinematic shallow depth of field and soft background bokeh, natural motion blur,
no jitter, no focus hunting.
```

Key patterns:
- "using the reference image as the exact look" — forces consistency
- Per-second timeline with specific physical actions
- "no slam", "no jitter", "no focus hunting" — negative instructions prevent artifacts
- Camera description separate from action
- "hold the pose for the final beat" — clean ending

### Abstract Ink — "чернила в силуэты" (Kling v2.1 Standard, 6s)

```
Action (6s timeline):
  • 0.0–1.5s: Close-up of swirling {color} ink, beginning to form the silhouette
    of a {subject}. Initial swirls focus on the {subject}'s nose and ears.
  • 1.5–3.0s: Slow push-in as the ink continues to swirl, starting to define
    the {subject}'s mane. Subtle ink particles disperse into the surrounding area.
  • 3.0–4.5s: Medium speed as the ink forms more of the {subject}'s silhouette,
    with gentle light reflections enhancing depth.
  • 4.5–6.0s: Final push-in, maintaining ink color and texture consistency,
    preserving silhouette clarity as the {subject}'s mane completes.

Camera: Slow push-in throughout. Focus on maintaining clarity of the {subject}'s
silhouette with subtle light reflections enhancing depth.
Lighting: Subtle, diffused lighting to soften shadows and draw attention
to the ink's transformation.
Feel: Photorealistic, ultra-detailed, capturing the elegance of ink movement
in a studio setting.
```

Key patterns:
- Placeholders ({color}, {subject}) for template reuse
- Progressive formation (nose/ears → mane → full silhouette)
- Single camera move (push-in) throughout
- "maintaining consistency" / "preserving clarity" — anti-artifact instructions

## Discover Workflow Format

Discover uses labeled lines (different from template timeline):

```
Subject: [who/what is in frame at the start]
Motion: [the FULL sequence with timing]
Camera: [one movement or static]
Speed: [slow/medium/fast]
Details: [secondary effects — particles, debris, reflections]
Continuity: [preservation instructions]
```

Each prompt = one complete video from start to finish. All prompts tell the same story with different camera/speed/style variations.

## Models on fal.ai

| Model | Best for |
|-------|----------|
| **Kling O3 Standard** | Multi-shot continuity (up to 6 shots), transitions |
| **Kling v3 Standard** | Physics (water, fire, smoke), hands |
| **Grok Imagine Video** | Budget, flexible duration 1-15s |
| **Wan 2.5/2.6** | Budget, 1080p, fast |
| **Veo 3.1** | Lip sync, talking head, natural performances |

### Sources
- https://fal.ai/learn/devs/kling-2-6-pro-prompt-guide
- https://leonardo.ai/news/kling-ai-prompts/
- https://www.veed.io/learn/kling-ai-prompting-guide
- https://app.klingai.com/global/quickstart/image-to-video-guide
