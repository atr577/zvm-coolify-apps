"""
Model configurations for external AI services.

Add new models by adding entries to the respective config dictionaries.
No code changes required in service classes.
"""

# Image generation models configuration
IMAGE_MODEL_CONFIGS = {
    "qwen-image": {
        "model": "Qubico/qwen-image",
        "task_type": "txt2img",
        "use_dimensions": True,  # width/height instead of aspect_ratio
        "dimensions": {
            "9:16": (576, 1024),
            "16:9": (1024, 576),
            "1:1": (1024, 1024),
            "4:3": (1024, 768),
            "3:4": (768, 1024),
        },
        "defaults": {"steps": 8, "flow_shift": 3}
    },
    "nano-banana-pro": {
        "model": "gemini",
        "task_type": "nano-banana-pro",
        "use_dimensions": False,
        "defaults": {"resolution": "1K", "output_format": "jpeg", "safety_level": "low"}
    },
}

# Video generation models configuration (KLING)
VIDEO_MODEL_CONFIGS = {
    "1.5": {"version": "1.5", "max_duration": 5},
    "1.6": {"version": "1.6", "max_duration": 5},
    "2.1": {"version": "2.1", "max_duration": 10},
    "2.1-master": {"version": "2.1-master", "max_duration": 10},
    "2.5": {"version": "2.5", "max_duration": 10},
    "2.6": {"version": "2.6", "max_duration": 10},
}

# LLM models configuration
LLM_MODEL_CONFIGS = {
    "gpt-4o-mini": {"model": "gpt-4o-mini", "max_tokens": 16384},
    "gpt-4o": {"model": "gpt-4o", "max_tokens": 128000},
    "claude-3-7-sonnet-20250219": {"model": "claude-3-7-sonnet-20250219", "max_tokens": 200000},
}
