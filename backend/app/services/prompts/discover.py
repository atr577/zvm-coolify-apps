"""Prompt templates for Discover workflow — image/video exploration + extraction."""


# --- Image: Round 1 (Wide exploration) ---

DISCOVER_IMAGE_WIDE_SYSTEM = """You are a creative director for short-form viral video content.
Your job is to generate diverse, visually striking image prompts based on a user's concept.

IMAGE FORMAT: {aspect_ratio} aspect ratio. Compose ALL prompts for this format.
- 9:16 = vertical/portrait (phone-first, subject fills height)
- 16:9 = horizontal/landscape (cinematic wide shots)
- 1:1 = square (centered, balanced composition)

RULES:
1. Generate exactly {count} image prompts, each unique and diverse
2. Each prompt should be a complete, detailed image description in ENGLISH
3. Vary these dimensions across prompts:
   - Camera angle (close-up, wide, bird's eye, low angle, dutch angle)
   - Lighting (dramatic side light, soft natural, neon, golden hour, high contrast)
   - Composition (centered, rule of thirds, symmetrical, dynamic diagonal)
   - Style (photorealistic, cinematic, hyper-detailed, editorial)
   - Object/subject variation within the concept
4. Every prompt must be suitable for image-to-video (clear subject, implied motion potential)
5. Compose for {aspect_ratio} — mention framing/orientation in each prompt
6. Keep each prompt 50-120 words
7. Do NOT include text overlays, watermarks, or UI elements in prompts

Return JSON:
{{
  "prompts": [
    "prompt text 1",
    "prompt text 2"
  ]
}}"""


def build_discover_wide_prompt(concept: str, count: int = 10) -> str:
    """Build user prompt for wide exploration round."""
    return f"""USER CONCEPT:
{concept}

Generate {count} diverse image prompts exploring this concept from different angles, styles, and compositions.
Each prompt should be a standalone image description that could work as the first frame of a short viral video.
Make them VERY different from each other — explore the creative space widely."""


# --- Image: Round 1 with refined prompt ---

DISCOVER_IMAGE_REFINED_SYSTEM = """You are a creative director for short-form viral video content.
You receive a detailed, pre-refined image generation prompt. Your job is to generate variations
that PRESERVE the core direction while introducing visual variety.

IMAGE FORMAT: {aspect_ratio} aspect ratio. Compose ALL prompts for this format.

RULES:
1. Generate exactly {count} image prompts
2. Each prompt MUST preserve: subject, action, environment, style, and quality keywords from the base prompt
3. Vary ONLY these dimensions across prompts:
   - Camera angle (slightly different angles: front, 3/4, low, eye-level)
   - Lighting variation (same character but different intensity/direction)
   - Moment variation (slightly different timing within the same action)
   - Detail emphasis (focus on different textures or elements)
4. Do NOT wildly diverge — all prompts should feel like the same scene shot differently
5. Keep each prompt 80-150 words, in ENGLISH
6. Preserve negative constraints (no text, no watermarks, etc.) from the base prompt
7. Preserve quality and style keywords from the base prompt

Return JSON:
{{
  "prompts": [
    "prompt text 1",
    "prompt text 2"
  ]
}}"""


def build_discover_refined_prompt(refined_prompt: str, count: int = 4) -> str:
    """Build user prompt for round 1 when refined prompt is available."""
    return f"""BASE PROMPT (refined by user):
{refined_prompt}

Generate {count} variations of this prompt. Keep the same subject, action, environment, style, and quality.
Vary camera angle, lighting direction, moment timing, and detail emphasis.
Each variation should feel like the same scene photographed from a different perspective."""


# --- Image: Round 2+ (Narrowing) ---

DISCOVER_IMAGE_NARROW_SYSTEM = """You are a creative director refining image prompts based on user preferences.
The user has selected favorites and rejected others from a previous round. Your job is to generate NEW prompts
that are closer to what the user likes, while still introducing creative variation.

IMAGE FORMAT: {aspect_ratio} aspect ratio. Compose ALL prompts for this format.

ANALYSIS APPROACH:
1. Study what the SELECTED prompts have in common (angle, lighting, style, composition, subject treatment)
2. Study what the REJECTED prompts had that the user didn't like
3. Generate new prompts that match the preferred patterns but explore new variations within that space
4. If user provided text feedback, prioritize those directions

RULES:
1. Generate exactly {count} new prompts
2. Each prompt 50-120 words, in ENGLISH, composed for {aspect_ratio}
3. 70% of prompts should be close to selected preferences
4. 30% of prompts should push boundaries slightly (creative exploration within the preferred direction)
5. Do NOT repeat any of the previous prompts verbatim
6. Keep the core concept but refine style, angle, lighting per user taste

Return JSON:
{{
  "prompts": [
    "prompt text 1"
  ]
}}"""


def build_discover_narrow_prompt(
    concept: str,
    selected_prompts: list[str],
    rejected_prompts: list[str],
    feedback: str | None = None,
    count: int = 10,
) -> str:
    """Build user prompt for narrowing round."""
    feedback_section = ""
    if feedback:
        feedback_section = f"""
USER FEEDBACK (prioritize this):
{feedback}
"""

    return f"""ORIGINAL CONCEPT:
{concept}

SELECTED (user liked these):
{chr(10).join(f'- {p}' for p in selected_prompts)}

REJECTED (user did NOT like these):
{chr(10).join(f'- {p}' for p in rejected_prompts)}
{feedback_section}
Generate {count} NEW image prompts that are closer to the user's preferences while maintaining creative diversity.
Do not repeat previous prompts. Refine the direction based on selection patterns and feedback."""


# --- Video: Mini-scenario generation ---

DISCOVER_VIDEO_SYSTEM = """You are a motion prompt engineer for image-to-video AI models (Kling, Veo, Hailuo, Minimax).

You receive a reference image (described by its prompt) and the user's refined concept.
Your job: write SHORT, TECHNICAL motion prompts in LABELED FORMAT.

VIDEO FORMAT: {aspect_ratio} aspect ratio.

IMAGE-TO-VIDEO MODELS — CAPABILITIES:
- One continuous shot (NO cuts, NO montage, NO angle switches)
- Simple subject motion (descends, rotates, deforms, walks, falls)
- One camera movement (static, slow push-in, pull-out, orbit, pan, tilt)
- 5-10 seconds = 1-2 actions maximum
- Approximate physics

CANNOT DO: multiple angles, sound, complex action chains, precise timecodes, text/UI.

OUTPUT FORMAT — each prompt must use these labeled lines:
Subject: [who/what is in frame]
Motion: [what physically moves/changes, 1-2 actions, direct verbs]
Camera: [one movement or static]
Speed: [slow/medium/fast]
Details: [secondary effects — particles, debris, reflections, wind]
Continuity: [preservation instructions]

GOOD EXAMPLE:
"Subject: industrial hydraulic press, bowling ball
Motion: press descends steadily onto ball, ball surface cracks and deforms under pressure
Camera: static, subtle push-in
Speed: slow
Details: small fragments fall to sides, dust rises from impact point
Continuity: maintain consistent lighting, preserve object proportions, no morphing"

GOOD EXAMPLE:
"Subject: woman in black dress, Porsche 911
Motion: woman opens car door smoothly, steps out with confidence, stands upright
Camera: slow dolly out
Speed: medium
Details: dress fabric moves naturally with body, hair shifts with movement
Continuity: preserve face identity, consistent lighting, no warping"

GOOD EXAMPLE:
"Subject: golden honey, stack of pancakes
Motion: honey pours from above onto pancakes, drips slowly down the sides
Camera: static top-down
Speed: slow
Details: steam rises gently, honey catches light with glossy reflections
Continuity: maintain food colors and textures, stable lighting"

BAD (DO NOT):
- Literary prose ("looms above with ceremonial slowness")
- Sound descriptions ("a resounding crack echoes")
- Multiple camera moves ("cuts to close-up, then pulls back")
- Fake timecodes ("at 2 seconds... at 4 seconds...")
- Metaphors ("like colored stars", "shower of fragments")

RULES:
1. Generate exactly {count} motion prompts
2. Each prompt MUST use the labeled format above
3. Motion line: direct verbs, 1-2 actions only, physically plausible
4. Camera line: ONE movement (or "static")
5. Continuity line: ALWAYS include — prevents AI artifacts
6. Vary across prompts: motion intensity, camera style, detail focus

Return JSON:
{{
  "prompts": [
    "Subject: ...\\nMotion: ...\\nCamera: ...\\nSpeed: ...\\nDetails: ...\\nContinuity: ..."
  ]
}}"""


def build_discover_video_prompt(
    image_prompt: str,
    count: int = 6,
    selected_prompts: list[str] | None = None,
    rejected_prompts: list[str] | None = None,
    feedback: str | None = None,
    direction: str | None = None,
    blocks: dict | None = None,
) -> str:
    """Build user prompt for video motion generation."""
    context = f"""WINNING IMAGE (first frame):
{image_prompt}"""

    if blocks:
        context += "\n\nMOTION CONTEXT (from user's refinement):"
        for key in ['subject', 'action', 'moment', 'environment', 'camera']:
            block = blocks.get(key, {})
            value = block.get('value')
            if value:
                label = key.upper()
                context += f"\n- {label}: {value}"

    if direction:
        context += f"""

USER DIRECTION (what should happen):
{direction}"""

    context += f"""

Generate {count} short motion prompts. Describe ONLY what moves/changes from this static image.
Use ACTION and MOMENT as the starting point — what happens NEXT?"""

    if selected_prompts:
        context += f"""

PREVIOUSLY SELECTED (user liked these motions):
{chr(10).join(f'- {p}' for p in selected_prompts)}

PREVIOUSLY REJECTED (user did NOT like):
{chr(10).join(f'- {p}' for p in (rejected_prompts or []))}

Generate new motion prompts closer to what the user liked."""

    if feedback:
        context += f"""

USER FEEDBACK:
{feedback}"""

    return context


# --- Extraction: Template from winning combo ---

DISCOVER_EXTRACTION_SYSTEM = """You are a template engineer for AI video generation.
Given a winning image prompt AND a video prompt, extract REUSABLE TEMPLATES for both.

Your job:
1. Identify the FIXED elements (always present): lighting style, camera angle, composition, quality keywords
2. Identify the VARIABLE elements (what changes between videos): the main subject/object, colors, specific details
3. Create a base_prompt (image template) with {{slot_name}} placeholders for variable elements
4. Create a DETAILED video_template_prompt with timeline, camera work, and the SAME {{slot_name}} placeholders
5. Create a variation_prompt that instructs an LLM how to fill those slots

CRITICAL FOR VIDEO TEMPLATE:
- The video prompt often contains specific objects (e.g. "records", "phone", "apple") — you MUST replace them with {{slot}} placeholders
- Use the SAME slot names in both image and video templates
- VIDEO MUST INCLUDE: second-by-second timeline, camera instructions, focus details
- Timeline MUST match the exact duration specified in the user prompt (NOT the example durations!)
- Keep the cinematic direction, movements, timing, and atmosphere — only replace the SUBJECT/OBJECT references

RULES:
- Use descriptive slot names: {{object}}, {{material}}, {{color_scheme}}, {{environment}}
- Keep 1-3 slots (not more, templates should be focused)
- Both base_prompt and video_template_prompt must use the SAME slots
- Write everything in ENGLISH
- IMPORTANT: Adapt timeline to match the specified video duration (e.g., 5s, 6s, 10s)

=== EXAMPLE 1: Person + Vehicle (cinematic) ===

video_template_prompt example:
"Action (10s timeline):
 • 0.0–2.0s: She sits in the {{vehicle}}, hands on wheel, engine idling. She gazes ahead with calm confidence, then turns toward camera.
 • 2.0–4.0s: She opens door and steps out elegantly, straightens posture with subtle smile.
 • 4.0–6.5s: She walks 3-4 confident steps along the {{vehicle}}, trailing fingers across the surface. Wind catches her hair.
 • 6.5–8.5s: She reaches the front, turns to face camera at 3/4 angle. Leans back casually against {{vehicle}}.
 • 8.5–10.0s: She looks slightly upward with composed, thoughtful expression. Hold the pose — cinematic beat.

Camera: Gimbal-stabilized. Starts medium-close, pulls back smoothly as she exits, tracks alongside during walk, settles wider at final pose. Subtle slow dolly movement.
Focus: Locked on face/upper body, cinematic shallow depth of field, soft background bokeh, natural motion blur. No jitter, no focus hunting."

=== EXAMPLE 2: Destruction / Satisfying (phone realism, viral UGC) ===

video_template_prompt example:
"Action (8s timeline):
 • 0.0–1.5s: Overhead POV from phone held above — {{object}} arranged in frame. Slight handheld micro-drift. {{material}} surfaces show phone-typical sharpening. Ambient machine hum. Auto-exposure settling.
 • 1.5–3.0s: First {{object}} slides toward shredder — physics match real {{material}} weight. Phone struggles with dynamic range. Subtle digital stabilization visible. Anticipation beat before contact.
 • 3.0–5.0s: Impact — teeth engage {{material}} with authentic deformation. Phone camera reacts: brief auto-focus hunt, auto-exposure flicker. High-framerate slow-mo feel. Fragments launch with correct physics, rolling shutter on fast edges.
 • 5.0–6.5s: Peak destruction — {{material}} shreds realistically. Phone HDR processing on highlights, noise reduction smooths particles slightly. Vertical 9:16 frame.
 • 6.5–8.0s: Aftermath — debris settles with real gravity. Handheld drift continues. Phone re-stabilizes exposure. Next {{object}} edges into frame.

Camera: Handheld overhead — natural micro-shake from human arm. Digital OIS smoothing with slight wobble-correction artifacts. NOT tripod, NOT gimbal — real person filming.
Sensor: Phone characteristics — deep DOF (no cinematic bokeh), computational sharpening, slight highlight clipping, shadow noise, 9:16 vertical native.
Lighting: Ambient only, no pro setup. Phone auto-white-balance may shift. Colors accurate but phone-processed (slightly saturated).
Feel: UGC aesthetic. Viral-ready. Authentic, not produced."

=== END EXAMPLES ===

STYLE SELECTION — choose based on content:
- Person/model/fashion → cinematic gimbal, smooth tracking, shallow DOF, polished
- Destruction/satisfying/shredder → phone UGC, handheld micro-shake, deep DOF, authentic
- Animal/pet/nature → stable with subject tracking, natural movement, documentary feel
- Action/sports/fast motion → dynamic handheld, quick pans, motion blur embraced
- Product/object reveal → smooth dolly/orbit, controlled lighting, studio precision
- Comedy/surprise/reaction → phone POV, authentic shakiness, spontaneous feel

Mix styles if content requires it. The goal is AUTHENTIC feel that matches the content type.

Return JSON:
{{
  "base_prompt": "image template with {{slot}} placeholders",
  "video_template_prompt": "DETAILED video template with timeline, camera, focus — using SAME {{slot}} placeholders",
  "variation_prompt": "Instructions for generating variants...",
  "slot_names": ["slot1", "slot2"],
  "slot_examples": {{
    "slot1": ["example1", "example2", "example3", "example4", "example5"],
    "slot2": ["example1", "example2", "example3"]
  }}
}}"""


def build_discover_extraction_prompt(
    winning_image_prompt: str,
    winning_video_prompt: str | None = None,
    video_duration: str = "5s",
    aspect_ratio: str = "9:16",
) -> str:
    """Build user prompt for template extraction."""
    video_section = ""
    if winning_video_prompt:
        video_section = f"""

WINNING VIDEO/MOTION PROMPT:
{winning_video_prompt}"""

    # Parse duration to seconds
    duration_sec = int(video_duration.replace("s", "")) if video_duration else 5

    return f"""WINNING IMAGE PROMPT:
{winning_image_prompt}
{video_section}

VIDEO SETTINGS:
- Duration: {duration_sec} seconds (timeline MUST fit this duration exactly)
- Aspect ratio: {aspect_ratio}

Extract a reusable template from this winning prompt.
Identify what should stay fixed (the "recipe") and what should vary (the "ingredients").
IMPORTANT: The video_template_prompt timeline MUST be exactly {duration_sec} seconds total."""


# --- Prompt Refinement ---

# Block constants
CREATIVE_BLOCKS = ["subject", "action", "moment", "environment"]
TECHNICAL_BLOCKS = ["camera", "lighting", "style", "format", "details"]
ALL_BLOCKS = CREATIVE_BLOCKS + TECHNICAL_BLOCKS
ALWAYS_RELEVANT = ["subject", "camera", "lighting", "style"]


DISCOVER_REFINEMENT_SYSTEM = """You are a creative prompt analyst for AI image generation.

Your job: analyze a user's concept and break it down into structured blocks for a high-quality image prompt.

BLOCKS TO ANALYZE:
1. Subject — main subject/object (WHO/WHAT is in frame)
2. Action — what's happening (dynamic aspect, movement)
3. Moment — which exact moment to capture (timing)
4. Environment — where it's happening (location, surroundings)
5. Camera — angle, distance, composition
6. Lighting — light source, character, mood
7. Style — visual style (photorealistic, cinematic, anime, etc.)
8. Format — aspect ratio, frame (DO NOT include, handled by system)
9. Details — textures, materials, particles, fine elements

TASK:
1. Parse the concept — extract what's already specified
   - If concept clearly states the subject → auto_filled
   - If concept implies action → auto_filled
   - Values must be in ENGLISH even if concept is in another language
2. Determine which blocks are RELEVANT:
   - Subject, Camera, Lighting, Style are ALWAYS relevant
   - Action: skip if concept is static (portrait, still life)
   - Moment: skip if only one possible moment (static scene, no timeline)
   - Environment: skip if abstract/studio/no location implied
   - Details: skip for simple concepts with no specific textures
3. For CREATIVE blocks that need user input (no clear answer from concept):
   - Write a clear question in the user's detected language
   - Provide exactly 4 diverse options (in ENGLISH, concise, 5-15 words each)
   - CRITICAL: questions and options must be SPECIFIC to this concept, not generic
4. For TECHNICAL blocks:
   - Generate appropriate values automatically based on concept (in ENGLISH)
   - Status: auto_generated
5. Do NOT include Format block — it is handled by the system

QUESTIONS AND OPTIONS — MUST BE CONCEPT-SPECIFIC:
Every question and option must directly relate to the user's concept. Never use generic options.

BAD (generic, useless):
  concept: "hydraulic press crushing objects"
  details question: "What details do you want?"
  details options: ["Detailed textures", "Visible particles", "Shiny metal", "Worn surfaces"]

GOOD (specific, helpful):
  concept: "hydraulic press crushing objects"
  details question: "Какие детали должны быть акцентированы?"
  details options: ["Oil dripping from hydraulic pistons", "Cracks spreading through crushed object", "Metal shavings and debris flying on impact", "Reflections on polished steel press surface"]

BAD (generic):
  concept: "boston terrier playing with toys"
  moment question: "Which moment?"
  moment options: ["Happy moment", "Funny moment", "Action moment", "Calm moment"]

GOOD (specific):
  concept: "boston terrier playing with toys"
  moment question: "Какой момент хотите запечатлеть?"
  moment options: ["Puppy mid-jump catching a ball in the air", "Toy knocked over, puppy frozen in guilty pose", "Tug-of-war with a rope toy, teeth bared playfully", "Puppy buried under pile of scattered toys"]

INPUT LANGUAGE: User may write in any language. Detect it. Ask questions in that language.
OUTPUT VALUES: All block values and options must be in ENGLISH.

Return JSON:
{{
  "detected_language": "ru",
  "relevant_blocks": ["subject", "action", ...],
  "blocks": {{
    "subject": {{
      "value": "extracted value or null",
      "status": "auto_filled | needs_input | auto_generated",
      "question": "question text in user language, or null",
      "options": ["opt1", "opt2", "opt3", "opt4"] or null
    }}
  }}
}}

IMPORTANT:
- Do NOT include "format" in blocks or relevant_blocks
- relevant_blocks must include at least: subject, camera, lighting, style
- Each block must have exactly the fields shown above
- Options must be exactly 4 items when provided
- NEVER generate generic options — every option must be specific to this concept"""


DISCOVER_COMPILE_SYSTEM = """You are a technical prompt engineer for AI image generation models (Flux, DALL-E, Midjourney, Kling).

Given a set of completed blocks describing a visual concept, compile them into a precise,
technical image generation prompt in ENGLISH.

WRITING STYLE — TECHNICAL, NOT LITERARY:
- Write as an image generation prompt, NOT as creative prose or a story
- Use concrete visual descriptors, not metaphors ("bright warm sunlight" not "a sun-drenched paradise")
- Specify camera, composition, and lighting technically ("low angle close-up, 35mm lens, shallow depth of field" not "an intimate glimpse into their world")
- Be direct and dense with visual information

COMPOSITION (derive from ALL blocks together):
- Specify depth of field based on subject and camera (e.g. "shallow DoF, bokeh background" or "deep focus, everything sharp")
- Include framing rules when appropriate (rule of thirds, centered, dynamic diagonal, leading lines)
- Describe background treatment (blurred, detailed, minimal, environmental context)
- Mention foreground/background relationship

QUALITY & STYLE KEYWORDS:
- Based on the Style block, include appropriate technical quality keywords
- Examples by style: photorealistic → "photorealistic, ultra-detailed, 8K"; cinematic → "cinematic lighting, film grain, anamorphic"; anime → "anime key visual, cel-shaded, vibrant"
- Do NOT hardcode "photorealistic" — match the style the user chose

RULES:
1. The prompt should be 80-150 words
2. Compose for the specified aspect ratio (mention framing orientation)
3. Incorporate ALL provided blocks — nothing should be lost
4. The prompt should work as a first frame for a short viral video
5. Do NOT mention block names — weave content together as a technical prompt
6. End with: style keywords, then quality keywords

Return JSON:
{{
  "refined_prompt": "the compiled prompt text"
}}"""


NEGATIVE_SUFFIX = "No text, no watermarks, no logos, no readable text overlays."
