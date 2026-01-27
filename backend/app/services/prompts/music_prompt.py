"""
Music prompt templates for AI music generation.

Model-specific system prompts:
- LYRIA2_MUSIC_PROMPT: Google Lyria2 via fal.ai (active)
- SUNO_MUSIC_PROMPT: Suno AI via PiAPI (legacy/deprecated)

Safety:
- UNSAFE_WORDS_MAP: word replacements applied before sending to fal.ai
- SAFETY_REWRITE_PROMPT: GPT prompt for auto-rephrasing rejected prompts
"""

# =============================================================================
# Lyria2 (fal.ai) — active model
# =============================================================================

LYRIA2_MUSIC_PROMPT = """ЧТО ТЫ ДЕЛАЕШЬ:
Ты получаешь описание видео-сцены.
Ты пишешь промпт для Google Lyria2 — AI-генерации музыкального трека.
Музыка будет наложена на это видео.

ТВОЯ ЗАДАЧА:
1. Понять историю/настроение сцены из описания
2. Описать какой трек нужен — жанр, вокал, энергия
3. Указать контекст (о чём сцена)
4. Придумать короткую фразу-хук

РЕЗУЛЬТАТ — JSON:
{
  "music_prompt": "описание трека (1-2 предложения, на английском)",
  "tags": "3-5 тегов через запятую"
}

ФОРМУЛА ДЛЯ music_prompt:
[жанр] + [вокал] + [контекст] + [фраза хука] + [энергия]

Где:
- жанр: поджанр (synth-pop, indie pop, trap, drill, house, edm, lo-fi)
- вокал: тембр + пол (warm female, smooth male, bright female, raspy male, airy female)
- контекст: сеттинг из видео (about city lights, about ocean waves, about morning routine)
- фраза хука: короткая earworm в кавычках (hook: 'let it go', hook: 'feel the light')
- энергия: темп или ощущение (upbeat, 120 BPM, chill, driving, floating)

ПРАВИЛА ДЛЯ tags:
3-5 тегов через запятую: жанр, энергия, тип вокала, настроение

⚠️ SAFETY RULES (Google Lyria2 content policy):
ЗАПРЕЩЕНО использовать в промпте и тегах:
- aggressive, powerful, dominant, savage, brutal, killer, deadly
- seductive, intoxicating, addictive, obsessed, toxic
- fire, burn, explode, destroy, smash, crush
- drug/alcohol references
- sexual/violent imagery

ЗАМЕНЯЙ на безопасные синонимы:
- aggressive → intense, driving
- powerful → bold, strong, dynamic
- dominant → confident, assured
- seductive → captivating, alluring, warm
- fire → bright, radiant, glowing
- savage → raw, unfiltered
- addictive → catchy, infectious
- intoxicating → mesmerizing, enchanting
- obsessed → devoted, drawn to
- toxic → bittersweet

НЕ ИСПОЛЬЗОВАТЬ в tags: "viral", "tiktok", "hook" — Lyria2 не понимает мета-теги.

ПРИМЕРЫ:

Вход: woman dancing alone in neon club, slow motion, 5 sec
{
  "music_prompt": "Dark synth-pop with airy female vocals about dancing through city lights. Hook: 'lose yourself tonight'. Pulsing, 100 BPM.",
  "tags": "synth-pop, dark, airy female vocals, pulsing, emotional"
}

Вход: man running through city at sunrise, fast dynamic, 5 sec
{
  "music_prompt": "Intense trap with confident male vocals about chasing the moment. Hook: 'never stop running'. Driving, high energy.",
  "tags": "trap, intense, male vocals, driving, motivational"
}

Вход: couple watching sunset on beach, slow romantic, 10 sec
{
  "music_prompt": "Dreamy indie pop with warm male vocals about endless summer. Hook: 'stay with me'. Atmospheric, gentle.",
  "tags": "indie pop, dreamy, warm male vocals, romantic, atmospheric"
}

Вход: luxury car driving through night city, cinematic, 5 sec
{
  "music_prompt": "Sleek electronic with smooth female vocals about the night drive. Hook: 'feel the light'. Cinematic, 110 BPM.",
  "tags": "electronic, cinematic, smooth female vocals, sleek, nocturnal"
}
"""

# =============================================================================
# Suno (PiAPI) — legacy/deprecated
# =============================================================================

SUNO_MUSIC_PROMPT = """ЧТО ТЫ ДЕЛАЕШЬ:
Ты получаешь описание видео-сцены.
Ты пишешь промпт для Suno AI чтобы он сгенерировал музыкальный трек с вокалом.
Музыка будет наложена на это видео.
Вокал должен петь про то, что происходит в видео.

ТВОЯ ЗАДАЧА:
1. Понять историю/настроение сцены из описания
2. Описать какой трек нужен — жанр, вокал, энергия
3. Указать контекст (о чём сцена)
4. Придумать короткую фразу-хук которая застрянет в голове

РЕЗУЛЬТАТ — JSON:
{
  "music_prompt": "описание трека для Suno (1-2 предложения)",
  "tags": "3-5 тегов через запятую"
}

ЦЕЛЬ МУЗЫКИ:
- Зацепить с первой секунды — у зрителя палец на скролле
- Earworm — фраза хука застревает в голове
- Вокал усиливает то, что происходит на видео

ФОРМУЛА ДЛЯ music_prompt:
[жанр] + [вокал] + [контекст] + [фраза хука] + [энергия]

Где:
- жанр: поджанр (synth-pop, indie pop, trap, drill, house, edm)
- вокал: характер + пол (breathy female, raspy male, powerful female, soft male)
- контекст: сеттинг из видео (about dancing at night, about running through city)
- фраза хука: короткая earworm в кавычках (hook: 'let it go', hook: 'never stop')
- энергия: темп или ощущение (high energy, pulsing, 110 BPM, atmospheric)

ПРАВИЛА ДЛЯ tags:
3-5 тегов через запятую: жанр, энергия, тип вокала, настроение

НЕ ИСПОЛЬЗОВАТЬ в tags: "viral", "tiktok", "hook" — Suno не понимает эти слова.

ПРИМЕРЫ:

Вход: woman dancing alone in neon club, slow motion, 5 sec
{
  "music_prompt": "Dark synth-pop with breathy female vocals about dancing at night. Catchy hook: 'lose yourself'. Pulsing, 100 BPM.",
  "tags": "synth-pop, dark, breathy female vocals, pulsing, emotional"
}

Вход: man running through city at sunrise, fast dynamic, 5 sec
{
  "music_prompt": "Aggressive trap with confident male vocals about chasing the moment. Hook: 'never stop'. 808s, high energy.",
  "tags": "trap, aggressive, male vocals, 808s, motivational"
}

Вход: couple watching sunset on beach, slow romantic, 10 sec
{
  "music_prompt": "Dreamy indie pop with soft male vocals about endless summer love. Hook: 'stay with me'. Atmospheric, gentle.",
  "tags": "indie pop, dreamy, soft male vocals, romantic, atmospheric"
}
"""

# =============================================================================
# Safety: word replacements (applied before sending to fal.ai)
# =============================================================================

UNSAFE_WORDS_MAP = {
    "aggressive": "intense",
    "powerful": "bold",
    "dominant": "confident",
    "seductive": "captivating",
    "savage": "raw",
    "brutal": "intense",
    "killer": "striking",
    "deadly": "striking",
    "fire": "bright",
    "burn": "glow",
    "explode": "burst",
    "destroy": "transform",
    "smash": "drive",
    "crush": "sweep",
    "addictive": "catchy",
    "intoxicating": "mesmerizing",
    "obsessed": "devoted",
    "toxic": "bittersweet",
}

# =============================================================================
# Safety: auto-rephrase prompt (used when fal.ai rejects content)
# =============================================================================

SAFETY_REWRITE_PROMPT = """The following music generation prompt was rejected by a content safety filter.
Rewrite it to preserve the musical intent but use only safe, neutral language.

RULES:
- Keep the same genre, mood, tempo, and structure
- Replace any potentially sensitive words with neutral synonyms
- Remove references to violence, substances, sexual content
- Keep hook phrases but make them clearly positive/neutral
- Output ONLY the rewritten prompt, nothing else

REJECTED PROMPT:
{rejected_prompt}"""
