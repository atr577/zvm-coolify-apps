"""
Mock responses for AI services.
Used in tests to avoid actual API calls.
"""

# ============ Story Generation ============

MOCK_STORY = {
    "concept": "A cute orange cat discovers the ocean for the first time, cautiously approaching the waves",
    "hook": "Watch this cat's hilarious reaction to seeing the ocean",
    "hook_type": "visual",
    "climax": "The cat gets splashed by a small wave and jumps back in surprise",
    "tone": "comedic",
    "pacing": "fast",
    "emotional_trigger": "laughter",
    "duration": 5
}

MOCK_STORY_DRAMATIC = {
    "concept": "A lone wolf stands on a cliff overlooking a vast valley at sunset",
    "hook": "The moment before everything changed",
    "hook_type": "visual",
    "climax": "The wolf howls as the sun dips below the horizon",
    "tone": "dramatic",
    "pacing": "slow",
    "emotional_trigger": "awe",
    "duration": 10
}

# ============ Description Generation ============

MOCK_DESCRIPTION = {
    "subject": {
        "type": "animal",
        "name": "Orange tabby cat",
        "appearance": "Fluffy orange fur, green eyes, curious expression",
        "pose": "Standing on all fours, tail up"
    },
    "setting": {
        "location": "Tropical beach",
        "time_of_day": "Golden hour",
        "weather": "Clear, sunny",
        "elements": ["white sand", "turquoise water", "small waves"]
    },
    "action": "Cat cautiously pawing at the wet sand near the waterline",
    "composition": {
        "shot_type": "Medium shot",
        "angle": "Eye level",
        "framing": "Cat centered, ocean in background"
    },
    "lighting": "Warm golden hour light from the left, soft shadows",
    "mood": "Playful, curious, lighthearted",
    "color_palette": ["orange", "turquoise", "gold", "white"]
}

# ============ Prompt Generation ============

MOCK_PROMPT = {
    "main_prompt": "Fluffy orange tabby cat standing on tropical beach at golden hour, curious expression, pawing at wet sand near waterline, turquoise ocean waves in background, warm sunlight, photorealistic, 8k, detailed fur texture",
    "negative_prompt": "blurry, dark, scary, aggressive, cartoon, anime, drawing, painting, watermark, text",
    "style_suffix": "cinematic lighting, shallow depth of field, professional photography"
}

# ============ Scenario Generation ============

MOCK_SCENARIO = {
    "scene_direction": "Cat walks slowly toward the water, pauses, then gets splashed",
    "motion_prompt": "Cat walking cautiously forward, stopping to sniff, jumping back surprised",
    "camera_movement": {
        "type": "dolly_in",
        "speed": "slow",
        "description": "Slow dolly in following the cat's movement"
    },
    "key_moments": [
        {"time": 0, "action": "Cat standing, looking at ocean"},
        {"time": 2, "action": "Cat approaches water cautiously"},
        {"time": 4, "action": "Wave splashes, cat jumps back"}
    ],
    "audio_notes": "Beach ambience, wave sounds, optional comedic sound effect on splash"
}

# ============ Adaptation Data ============

MOCK_ADAPTATION = {
    "instagram": {
        "caption": "When your cat sees the ocean for the first time 😹🌊 #CatsOfInstagram #BeachCat #FunnyPets",
        "hashtags": ["CatsOfInstagram", "BeachCat", "FunnyPets", "CatReaction", "OceanVibes"],
        "music_suggestion": "Upbeat, playful track"
    },
    "tiktok": {
        "caption": "POV: Your cat discovers water exists 💀 #fyp #cat #funny",
        "hashtags": ["fyp", "cat", "funny", "beachday", "catsoftiktok"],
        "sound_suggestion": "Trending funny sound or original audio"
    },
    "youtube": {
        "title": "Cat's HILARIOUS First Beach Experience! 🐱🏖️",
        "description": "Watch as this adorable orange tabby cat discovers the ocean for the first time...",
        "tags": ["cat", "funny cat", "beach", "pets", "cute animals"]
    }
}

# ============ Validation Results ============

MOCK_VALIDATION_PASS = {
    "status": "pass",
    "score": 85,
    "criteria_results": {
        "relevance": {"score": 90, "feedback": "Content matches theme well"},
        "clarity": {"score": 85, "feedback": "Clear and concise"},
        "engagement": {"score": 80, "feedback": "Good hook potential"}
    },
    "warnings": [],
    "errors": [],
    "recommendations": ["Consider adding more specific details about the setting"]
}

MOCK_VALIDATION_PASS_WITH_WARNINGS = {
    "status": "pass_with_warnings",
    "score": 70,
    "criteria_results": {
        "relevance": {"score": 75, "feedback": "Generally relevant"},
        "clarity": {"score": 65, "feedback": "Could be clearer"},
        "engagement": {"score": 70, "feedback": "Moderate engagement potential"}
    },
    "warnings": ["Hook could be stronger", "Consider faster pacing for TikTok"],
    "errors": [],
    "recommendations": ["Strengthen the opening hook", "Add more visual details"]
}

MOCK_VALIDATION_FAIL = {
    "status": "fail",
    "score": 40,
    "criteria_results": {
        "relevance": {"score": 30, "feedback": "Does not match theme"},
        "clarity": {"score": 50, "feedback": "Confusing structure"},
        "engagement": {"score": 40, "feedback": "Weak hook"}
    },
    "warnings": [],
    "errors": ["Content does not match the specified theme", "Missing required elements"],
    "recommendations": ["Regenerate with focus on the core theme"]
}

# ============ API Responses ============

MOCK_IMAGE_URL = "https://cdn.example.com/generated/image_12345.jpg"
MOCK_VIDEO_URL = "https://cdn.example.com/generated/video_12345.mp4"
MOCK_TASK_ID = "task_abc123xyz"

MOCK_AUDIO_VARIANTS = [
    "https://cdn.example.com/generated/video_audio_v1.mp4",
    "https://cdn.example.com/generated/video_audio_v2.mp4",
    "https://cdn.example.com/generated/video_audio_v3.mp4",
    "https://cdn.example.com/generated/video_audio_v4.mp4"
]

# ============ PiAPI Responses ============

MOCK_PIAPI_CHAT_RESPONSE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1704067200,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"concept": "test", "hook": "test hook"}'
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }
}

MOCK_PIAPI_TASK_CREATED = {
    "data": {
        "task_id": MOCK_TASK_ID
    }
}

MOCK_PIAPI_TASK_COMPLETED = {
    "data": {
        "task_id": MOCK_TASK_ID,
        "status": "completed",
        "output": {
            "video_url": MOCK_VIDEO_URL
        }
    }
}

MOCK_PIAPI_TASK_PROCESSING = {
    "data": {
        "task_id": MOCK_TASK_ID,
        "status": "processing"
    }
}

MOCK_PIAPI_IMAGE_COMPLETED = {
    "data": {
        "task_id": MOCK_TASK_ID,
        "status": "completed",
        "output": {
            "image_urls": [MOCK_IMAGE_URL]
        }
    }
}

MOCK_PIAPI_SOUND_COMPLETED = {
    "data": {
        "task_id": MOCK_TASK_ID,
        "status": "completed",
        "output": {
            "works": [
                {"video": {"resource": url}} for url in MOCK_AUDIO_VARIANTS
            ]
        }
    }
}
