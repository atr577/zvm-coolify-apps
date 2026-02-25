# Video Prompt: Medals Melt and Mix

Model: Veo 3.1 (fal.ai, first-last-frame-to-video) | Duration: 8s | Aspect: 9:16

## Prompt (attempt 2)

```
A hand grips a metal palette knife and slowly drags it through three thick metallic liquid pools
— gold, silver and bronze — on a dark surface,
swirling and folding the colors together in smooth deliberate circular motions.
The metallic liquids blend into shimmering streaks with each stroke of the knife.
Slow, continuous hand movement throughout. The hand never stops moving.
Top-down flat lay, static camera, close-up.
```

## Frames

- Start: `results/frames/start_frame.jpg` (3 Olympic medals on dark surface)
- End: `results/frames/end_frame.jpg` (uniform deep teal with gold shimmer)

## Notes

- Veo 3.1 endpoint: `fal-ai/veo3.1/first-last-frame-to-video` (NOT `/image-to-video`)
- Start+end frame гарантирует полный цикл: medals → teal shimmer
- **Attempt 1 → 2 changes:** убрано описание трансформации solid→liquid (medals melting). Start+end frame задают состояния, промпт описывает только MOTION (рука мешает). Упрощено до одного действия — mixing. Убрано "slowly melt" — модель не должна трансформировать объекты, только интерполировать между кадрами.
- "The hand never stops moving" — проверенная фраза из v2 промпта
- Veo 3.1 лучший для жидкостей (подтверждено в v1)
- ~60 слов — компактнее, одно действие

## Fallback

Если Veo 3.1 не справится с "melting medals" (слишком сложная трансформация):
- Minimax Hailuo-02 10s с `end_image_url` как альтернатива
- Может потребоваться промежуточный кадр (medals partially melted) для плавности

## Result

- TBD
