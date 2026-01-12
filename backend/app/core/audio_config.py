"""
Audio Configuration.

Defines audio types, providers, and their valid combinations.
"""

from typing import Literal, Dict, List

# Audio mode types (what kind of audio to generate)
AudioType = Literal["none", "scene", "music", "voiceover", "auto"]

# Audio providers (who generates the audio)
AudioProvider = Literal["kling", "ai_music"]

# Which providers are available for each audio type
AUDIO_TYPE_PROVIDERS: Dict[AudioType, List[AudioProvider]] = {
    "none": [],  # No audio needed
    "scene": ["kling"],  # Sound effects - only kling
    "music": ["kling", "ai_music"],  # Background music - kling or ai_music
    "voiceover": ["kling"],  # Voice narration - only kling
    "auto": ["kling", "ai_music"],  # AI decides - both available
}

# Default provider for each audio type
DEFAULT_PROVIDER: Dict[AudioType, AudioProvider] = {
    "none": "kling",  # N/A but need a default
    "scene": "kling",
    "music": "kling",
    "voiceover": "kling",
    "auto": "kling",
}


def is_valid_combination(audio_type: AudioType, provider: AudioProvider) -> bool:
    """
    Check if audio_type and provider combination is valid.

    Args:
        audio_type: The type of audio (none, scene, music, voiceover, auto)
        provider: The provider to use (kling, ai_music)

    Returns:
        True if combination is valid, False otherwise
    """
    if audio_type not in AUDIO_TYPE_PROVIDERS:
        return False

    available = AUDIO_TYPE_PROVIDERS[audio_type]
    return provider in available


def get_available_providers(audio_type: AudioType) -> List[AudioProvider]:
    """
    Get list of available providers for an audio type.

    Args:
        audio_type: The type of audio

    Returns:
        List of available provider names
    """
    return AUDIO_TYPE_PROVIDERS.get(audio_type, [])


def get_default_provider(audio_type: AudioType) -> AudioProvider:
    """
    Get default provider for an audio type.

    Args:
        audio_type: The type of audio

    Returns:
        Default provider name
    """
    return DEFAULT_PROVIDER.get(audio_type, "kling")


def is_ai_music_available() -> bool:
    """
    Check if ai_music provider is available.

    ai_music requires OPENAI_API_KEY to be configured for hook analysis.

    Returns:
        True if ai_music can be used, False otherwise
    """
    from app.core.config import settings

    return bool(settings.OPENAI_API_KEY)


def get_audio_options() -> Dict:
    """
    Get full audio options for frontend.

    Returns dict with:
        - types: list of audio types
        - providers: dict mapping type to available providers
        - defaults: dict mapping type to default provider
        - ai_music_available: bool
    """
    # Filter out ai_music if not available
    ai_available = is_ai_music_available()

    providers = {}
    for audio_type, provider_list in AUDIO_TYPE_PROVIDERS.items():
        if ai_available:
            providers[audio_type] = provider_list
        else:
            # Remove ai_music if not available
            providers[audio_type] = [p for p in provider_list if p != "ai_music"]

    return {
        "types": list(AUDIO_TYPE_PROVIDERS.keys()),
        "providers": providers,
        "defaults": DEFAULT_PROVIDER,
        "ai_music_available": ai_available,
    }
