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

DISCOVER_VIDEO_SYSTEM = """You are a director for short-form viral videos (5-8 seconds).
Given a winning image (the first frame) and optional user direction, write detailed VIDEO SCENARIOS — mini-scripts that describe WHAT HAPPENS second by second.

VIDEO FORMAT: {aspect_ratio} aspect ratio.

WHAT A GOOD SCENARIO INCLUDES:
- **Action beats**: what physically happens to the subject, step by step (e.g. "teeth grip the phone → pause → violent pull inward → shower of fragments")
- **Camera work**: movement, angle changes, focus shifts
- **Timing & pacing**: where the tension builds, where the payoff hits
- **Sensory details**: sparks, cracks, debris, reflections, textures, particles
- **Emotional arc**: anticipation → climax → aftermath (or surprise → reaction)

RULES:
1. Generate exactly {count} scenario variations
2. Each scenario should be 80-150 words in ENGLISH
3. Every scenario starts from the given image as frame 1
4. Vary across scenarios: action intensity, camera style, pacing, emotional tone
5. Think about what makes a 5-8 second clip IMPOSSIBLE TO SCROLL PAST
6. Write in present tense, cinematic style ("The blade descends..." not "A blade should descend...")
7. Do NOT include text overlays, watermarks, or UI elements

Return JSON:
{{
  "prompts": [
    "scenario text 1"
  ]
}}"""


def build_discover_video_prompt(
    image_prompt: str,
    count: int = 6,
    selected_prompts: list[str] | None = None,
    rejected_prompts: list[str] | None = None,
    feedback: str | None = None,
    direction: str | None = None,
) -> str:
    """Build user prompt for video scenario generation."""
    context = f"""WINNING IMAGE (first frame):
{image_prompt}"""

    if direction:
        context += f"""

USER DIRECTION (what should happen in the video):
{direction}

Generate {count} detailed video scenarios based on this direction. Create variations in camera work, pacing, and intensity — but all should follow the user's creative vision."""
    else:
        context += f"""

Generate {count} diverse video scenarios for this image. Imagine different ways this scene could come alive in a 5-8 second viral clip."""

    if selected_prompts:
        context += f"""

PREVIOUSLY SELECTED SCENARIOS (user liked these):
{chr(10).join(f'- {p}' for p in selected_prompts)}

PREVIOUSLY REJECTED SCENARIOS (user did NOT like these):
{chr(10).join(f'- {p}' for p in (rejected_prompts or []))}

Generate new scenarios closer to what the user liked. Keep the creative direction but vary execution."""

    if feedback:
        context += f"""

USER FEEDBACK (prioritize this):
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
