"""
Model configurations for external AI services.

Add new models by adding entries to the respective config dictionaries.
No code changes required in service classes.
"""

# Image generation models configuration
IMAGE_MODEL_CONFIGS = {
    # fal.ai models
    "fal-ai/nano-banana-pro": {
        "provider": "fal.ai",
        "model": "fal-ai/nano-banana-pro",
        "use_dimensions": False,
        "defaults": {"resolution": "1K", "output_format": "jpeg"}
    },
    "fal-ai/flux-pro/v1.1-ultra": {
        "provider": "fal.ai",
        "model": "fal-ai/flux-pro/v1.1-ultra",
        "use_dimensions": False,
        "defaults": {"aspect_ratio": "9:16"}
    },
    # Legacy PiAPI models (deprecated)
    "qwen-image": {
        "provider": "piapi",
        "model": "Qubico/qwen-image",
        "task_type": "txt2img",
        "use_dimensions": True,
        "dimensions": {
            "9:16": (576, 1024),
            "16:9": (1024, 576),
            "1:1": (1024, 1024),
            "4:3": (1024, 768),
            "3:4": (768, 1024),
        },
        "defaults": {"steps": 8, "flow_shift": 3},
        "deprecated": True
    },
    "nano-banana-pro": {
        "provider": "piapi",
        "model": "gemini",
        "task_type": "nano-banana-pro",
        "use_dimensions": False,
        "defaults": {"resolution": "1K", "output_format": "jpeg", "safety_level": "low"},
        "deprecated": True
    },
}

# Video generation models configuration
VIDEO_MODEL_CONFIGS = {
    # fal.ai models
    "fal-ai/veo3.1/image-to-video": {
        "provider": "fal.ai",
        "model": "fal-ai/veo3.1/image-to-video",
        "max_duration": 8,
        "supports_audio": True
    },
    "fal-ai/kling-video/v2.1/image-to-video": {
        "provider": "fal.ai",
        "model": "fal-ai/kling-video/v2.1/image-to-video",
        "max_duration": 10,
        "supports_audio": False
    },
    # Legacy PiAPI KLING models (deprecated)
    "kling-1.5": {"provider": "piapi", "version": "1.5", "max_duration": 5, "deprecated": True},
    "kling-1.6": {"provider": "piapi", "version": "1.6", "max_duration": 5, "deprecated": True},
    "kling-2.1": {"provider": "piapi", "version": "2.1", "max_duration": 10, "deprecated": True},
    "kling-2.1-master": {"provider": "piapi", "version": "2.1-master", "max_duration": 10, "deprecated": True},
    "kling-2.5": {"provider": "piapi", "version": "2.5", "max_duration": 10, "deprecated": True},
    "kling-2.6": {"provider": "piapi", "version": "2.6", "max_duration": 10, "deprecated": True},
}

# Music generation models configuration
MUSIC_MODEL_CONFIGS = {
    # fal.ai models
    "fal-ai/lyria2": {
        "provider": "fal.ai",
        "model": "fal-ai/lyria2",
        "max_duration": 30,
        "format": "wav"
    },
    # Legacy PiAPI models (deprecated)
    "suno": {"provider": "piapi", "model": "suno", "deprecated": True},
    "music-u": {"provider": "piapi", "model": "music-u", "deprecated": True},
}

# LLM models configuration
LLM_MODEL_CONFIGS = {
    "gpt-4o-mini": {"provider": "openai", "model": "gpt-4o-mini", "max_tokens": 16384},
    "gpt-4o": {"provider": "openai", "model": "gpt-4o", "max_tokens": 128000},
    "claude-3-7-sonnet-20250219": {"provider": "anthropic", "model": "claude-3-7-sonnet-20250219", "max_tokens": 200000},
}
