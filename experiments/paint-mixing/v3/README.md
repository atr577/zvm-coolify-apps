# Paint Mixing v3 — Olympic Ring Colors → Gold

Colors: cobalt blue, yellow, black, green, red → brown → gold with glitter

## Concept

5 Olympic ring colors mixed together = muddy brown. Twist: gold paint poured in, transforms everything to shimmering gold. Hooked version starts from the gold reveal.

## Final Output

- **`results/final/final_hooked.mp4`** — hooked version (starts at 16s, gold reveal first)
- `results/final/final_with_cta.mp4` — straight version (chronological)
- CTA: "What color do the Olympic rings make?" — cyan (#00E5FF), fontsize 34

## Pipeline

| Step | Model | Prompt | Result |
|------|-------|--------|--------|
| Frame 1 | Nano Banana Pro | `prompts/start-frame.md` | `results/frames/start_frame_*.json` |
| Frame 2 | Nano Banana Pro /edit | `prompts/mid-frame.md` | `results/frames/mid_frame_*.json` |
| Frame 3 | Nano Banana Pro /edit | `prompts/gold-pour-frame.md` | `results/frames/gold_pour_frame_*.json` |
| Frame 4 | Nano Banana Pro /edit | `prompts/end-frame.md` | `results/frames/end_frame_*.json` |
| Video 1 | Minimax Hailuo-02 6s | `prompts/video-1-mixing.md` | `results/video/video_1_mixing.mp4` |
| Video 2 | Minimax Hailuo-02 6s | `prompts/video-2-gold-pour.md` | `results/video/video_2_gold_pour.mp4` |
| Video 3 | Minimax Hailuo-02 6s | `prompts/video-3-gold-spread.md` | `results/video/video_3_gold_spread.mp4` |
| Music | Lyria2 + hook 18s | `prompts/music.md` | `results/music/music_hook.wav` |
| Assembly | FFmpeg concat + hook | `scripts/assemble_hooked.py` | `results/final/final_hooked.mp4` |

## Key Decisions

- 4 frames, 3 video segments (6s each) = 17.8s total
- Mid frame: uniform brown → gold pour frame: brown + gold stream (two /edit steps)
- Hand changes from palette knife to squeeze bottle between frame 2→3 (risk accepted)
- Music: lo-fi ambient with build-up (v1 cinematic prompt rejected)
- Hook: starts at 16s (gold reveal), then full process

## Cost

| Item | Cost |
|------|------|
| 4 frames (Nano Banana Pro) | ~$0.20 |
| 3 video segments (Minimax 6s × $0.30) | ~$0.90 |
| Music (Lyria2 × 2 attempts) | ~$0.20 |
| **Total** | **~$1.30** |

## Meta

See `meta.md` for YouTube title, description, tags.
