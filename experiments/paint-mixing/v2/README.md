# Paint Mixing v2 — Orange + Purple + White

Colors: orange, purple, white → pastel lavender

## Final Output

- **`results/final/final_hooked.mp4`** — hooked version (starts at 2.5s mid-mixing, "before" at end)
- `results/final/final_with_cta.mp4` — straight version (chronological)
- CTA: "What color will this make?" — cyan (#00E5FF), black stroke, 20% from top

## Pipeline

| Step | Model | Prompt | Result |
|------|-------|--------|--------|
| Start frame | Nano Banana Pro | `prompts/start-frame.md` | `results/frames/start_frame.jpg` |
| End frame | Nano Banana Pro /edit | `prompts/end-frame.md` | `results/frames/end_frame.jpg` |
| Video | Minimax Hailuo-02 10s | `prompts/video-minimax.md` | `results/video/video_minimax_10s.mp4` |
| Music | Lyria2 + hook extract | `prompts/music.md` | `results/music/music_hook_10s.wav` |
| Assembly | FFmpeg | `scripts/assemble_hooked.py` | `results/final/final_hooked.mp4` |

## Rejected Video Models

| Model | Issue | Prompt |
|-------|-------|--------|
| Veo 3.1 (8s) | Abrupt transition to end frame | `prompts/video-veo.md` |
| Kling O3 v1 | Hand frozen, only paint moves | `prompts/video-klingo3.md` (v1) |
| Kling O3 v2 | Hand moves but jerky | `prompts/video-klingo3.md` (v2) |

## Meta

See `meta.md` for YouTube title, description, tags.

## Scripts

| Script | Purpose |
|--------|---------|
| `generate_start_frame.py` | Nano Banana Pro image gen |
| `generate_end_frame.py` | Nano Banana Pro /edit |
| `generate_video.py` | Veo 3.1 (rejected) |
| `generate_video_klingo3.py` | Kling O3 (rejected) |
| `generate_video_minimax.py` | Minimax Hailuo-02 (winner) |
| `generate_music.py` | Lyria2 + hook extraction |
| `assemble_final.py` | Straight version assembly |
| `assemble_hooked.py` | Hooked version assembly (CUT_AT=2.5s) |
