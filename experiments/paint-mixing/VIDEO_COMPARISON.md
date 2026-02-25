# Paint Mixing — Video Model Comparison

Start frame (A2): 3 blobs (teal, magenta, yellow) — hand with stick
End frame: uniform teal-green — same composition

## All Generated Videos

| # | Model | Duration | Start+End | ~Cost | URL |
|---|-------|----------|-----------|-------|-----|
| 1 | Kling v3 Standard | 8s | No (start only) | $1.34 | [video](https://v3b.fal.media/files/b/0a8ed851/Q3-rca01MbBX7N-l3v_kP_output.mp4) |
| 2 | Minimax Hailuo-02 | 6s | No (start only) | $0.27 | [video](https://v3b.fal.media/files/b/0a8ed876/Mp6LdHmtKeZ9laU1BhIa2_output.mp4) |
| 3 | Minimax Hailuo-02 | 10s | No (start only) | $0.45 | [video](https://v3b.fal.media/files/b/0a8ed897/Ul6rdGL0_M_0QZ0Um6_aD_output.mp4) |
| 4 | Kling 2.6 Pro | 10s | No (start only) | $1.68 | [video](https://v3b.fal.media/files/b/0a8ed8b4/qOT6TRKcPUhBF_Row66Pg_output.mp4) |
| 5 | Kling v3 Standard | 10s | Yes | $1.68 | [video](https://v3b.fal.media/files/b/0a8ed919/fGri6S6QKMLycc17HKNPI_output.mp4) |
| 6 | Kling v3 Standard | 15s | Yes | $2.52 | [video](https://v3b.fal.media/files/b/0a8ed94c/C9Wt8a9K8Ca3toJ2BdLbZ_output.mp4) |
| 7 | Grok Imagine Video | 10s | No (start only) | $0.50-0.70 | [video](https://v3b.fal.media/files/b/0a8ed979/n0LD8JmIZbFFaiZdOfBy9_GnSH6EFe.mp4) |
| 8 | PixVerse v5.5 Transition | 10s | Yes | $1.20 | [video](https://v3b.fal.media/files/b/0a8ed982/oc97fUk6IXD78QN39qcel_output.mp4) |
| 9 | Kling O3 Standard | 10s | Yes | $1.68 | [video](https://v3b.fal.media/files/b/0a8ed9a7/gP6Jyix8sRvoOfJE594-z_output.mp4) |
| 10 | Veo 3.1 | 8s | Yes | $1.60 | [video](https://v3b.fal.media/files/b/0a8ed9b4/oduzvdO_JNfQhnIoBhJYA_a5aadc2b9837412ba05c5cbd74368a06.mp4) |

## Notes

- Models without end frame support (#1-4, #7) end mid-mix — incomplete arc
- Start+end frame approach (#5-6, #8-10) guides the video to show full mixing cycle
- Grok (#7) excluded from further testing — no end frame support
