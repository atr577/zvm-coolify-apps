# Image Prompts: Paint Mixing

Модель: Nano Banana Pro (fal.ai) | Aspect ratio: 9:16

Каждый промпт — первый кадр для i2v. Стартовое состояние: пигмент только что попал на белую базу, рука с инструментом готова мешать. Видео анимирует перемешивание.

## Шаблон

Структура по knowledge base: Subject → Action/State → Environment → Camera → Lighting → Composition → Style → Constraints.

Переменные: `{color}`, `{surface}`, `{tool}`.

```
Thick viscous {color} paint freshly poured into {surface} filled with white paint base,
pigment sitting on top in a dense blob, not yet mixed, sharp color boundary visible.
A hand gripping {tool}, tip touching the surface of the paint, about to begin stirring.
Clean studio tabletop, neutral grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, paint texture clearly visible.
Vertical 9:16, {surface} centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

**Терминология:** "top-down flat lay" вместо "bird's-eye view". Bird's eye = дистанция, широкий план. Top-down flat lay = close-up overhead, standard в product photography. Подтверждено в Nano Banana Pro prompt guide (пример: "top-down flatlay with matching kitchen props").

## Конкретные промпты

### Подход A: статичный старт (blob + рука готова мешать)

Рука с инструментом уже в кадре, кончик касается краски. Видео = начало перемешивания.

#### A1. Teal / банка / палочка

```
Thick viscous teal paint freshly poured into a round white paint can,
pigment sitting on top of white base in a dense irregular blob, not yet mixed, sharp color boundary visible.
A hand gripping a wooden stir stick, tip dipped into the paint surface, about to begin stirring.
Clean studio tabletop, matte light grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, glossy paint surface reflects light.
Vertical 9:16, paint can centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

#### A2. Magenta / палитра / мастихин

```
Thick viscous magenta paint squeezed onto a flat white ceramic palette,
bright pigment blob sitting on clean white surface, not yet spread, crisp color edge.
A hand holding a metal palette knife at a low angle, blade edge touching the paint.
Clean studio tabletop, matte light grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, wet paint surface with subtle sheen.
Vertical 9:16, palette centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

#### A3. Emerald green / стеклянная ёмкость / ложка

```
Thick viscous emerald green paint freshly poured into a clear glass mixing bowl,
bright green pigment sitting on top of white paint base, layered and unmixed, visible through glass walls.
A hand holding a silver spoon, bowl of spoon submerged in the paint.
Clean studio tabletop, matte dark grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, glass edges catch subtle highlights.
Vertical 9:16, glass bowl centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

### Подход B: динамичный старт (mid-pour stream)

Краска льётся тонкой струёй в белую базу. Момент удара. Видео = продолжение заливки + начало перемешивания.

#### B1. Cobalt blue / банка / stream

```
Thin stream of thick cobalt blue paint being poured from above into a round white paint can filled with white base,
blue paint hitting the white surface, small splash forming at the point of contact, first ripples spreading outward.
A hand visible at top edge of frame holding a small container tilted, pouring the blue paint.
Clean studio tabletop, matte warm grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, paint stream catches light.
Vertical 9:16, paint can centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

#### B2. Deep orange / палитра / squeeze

```
Thick deep orange paint being squeezed from a tube onto a flat white ceramic palette,
bright orange ribbon curling onto clean white surface, tube nozzle visible, paint still flowing.
A hand squeezing the paint tube from the top edge of frame.
Clean studio tabletop, matte light grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, fresh wet orange paint glistens.
Vertical 9:16, palette centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

#### B3. Violet / банка / pour

```
Thick violet paint being poured in a slow stream into a round white paint can filled with white base,
purple stream falling from above, creating a dense pool where it hits the white surface, colors sharply separated.
A hand tilting a small metal cup at the top of frame, pouring the violet paint.
Clean studio tabletop, matte neutral grey surface.
Top-down flat lay, close-up, straight down 90 degrees, shot from directly above.
Soft diffused studio lighting from two sides, no hard shadows, paint shows thick viscous texture.
Vertical 9:16, paint can centered in frame.
Photorealistic product photography, ultra-detailed.
No text, no watermarks, no logos.
```

## Заметки

- **"Top-down flat lay"** — правильная терминология для close-up overhead в product photography. "Bird's eye view" подразумевает дистанцию и широкий план. Подтверждено Nano Banana Pro prompt guide.
- **Руки в кадре:** рука входит с края кадра — видна частично (кисть + запястье), не целиком. Снижает риск AI-артефактов.
- **Подход A vs B:** A = спокойный старт, проще для генерации. B = динамичный hook (stream/pour), сильнее как первый кадр но сложнее. Нужно протестировать оба.
- **Почему "not yet mixed":** стартовый кадр для видео. Видео анимирует перемешивание.
- **Убран "8K":** Nano Banana Pro не управляется качеством через текстовый промпт, это параметр API.
- **Все промпты ~75-85 слов** — в рамках правила 50-150.
