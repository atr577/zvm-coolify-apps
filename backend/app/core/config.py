from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "REGGY"
    DEBUG: bool = True
    SECRET_KEY: str
    MOCK_MODE: bool = False
    LOG_LEVEL: str = "INFO"  # DEBUG for dev (full payloads), INFO for prod
    CACHE_API_RESPONSES: bool = True  # Сохранять ответы API для будущих моков
    API_CACHE_DIR: str = "data/api_cache"

    # PiAPI (единый провайдер для GPT + KLING)
    PIAPI_KEY: str = ""
    PIAPI_LLM_URL: str = "https://api.piapi.ai/v1"
    PIAPI_TASK_URL: str = "https://api.piapi.ai/api/v1"

    # Legacy AIMLAPI support (deprecated)
    AIMLAPI_KEY: str = ""

    # Модели (model-agnostic)
    LLM_MODEL: str = "gpt-4o-mini"  # gpt-4o-mini, gpt-4o, claude-3-7-sonnet-20250219
    VIDEO_MODEL: str = "kling-2.5"  # kling-1.5, kling-2.1, kling-2.5, kling-2.6
    IMAGE_MODEL: str = "qwen-image"  # qwen-image, nano-banana-pro
    MUSIC_MODEL: str = "suno"  # suno, music-u (Udio)

    # Legacy aliases
    GPT_MODEL: str = ""  # Deprecated: use LLM_MODEL
    KLING_MODEL: str = ""  # Deprecated: use VIDEO_MODEL

    # OpenAI Direct (for GPT-4o-audio-preview - not available via PiAPI)
    OPENAI_API_KEY: str = ""  # Optional: enables ai_music provider
    OPENAI_AUDIO_MODEL: str = "gpt-4o-audio-preview"  # Model for audio analysis

    # Storage paths (all relative to backend/)
    DATA_DIR: str = "data"
    TEMP_DIR: str = "data/temp"           # Temporary files (auto-cleanup)
    MEDIA_DIR: str = "data/media"         # Persistent media storage
    MEDIA_IMAGES_DIR: str = "data/media/images"
    MEDIA_VIDEOS_DIR: str = "data/media/videos"
    MEDIA_AUDIO_DIR: str = "data/media/audio"

    # Instagram OAuth
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""  # Deprecated: use OAuth flow instead
    INSTAGRAM_BUSINESS_ACCOUNT_ID: str = ""  # Deprecated: use OAuth flow instead

    # TikTok OAuth
    TIKTOK_CLIENT_ID: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_CLIENT_KEY: str = ""  # Deprecated: use TIKTOK_CLIENT_ID

    # YouTube OAuth
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/auth/youtube/callback"  # Deprecated: dynamic callback

    # Database
    DATABASE_URL: str = "sqlite:///./generator.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # File Storage
    UPLOAD_DIR: str = "data/uploads"
    GENERATED_DIR: str = "data/generated"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore deprecated env vars


settings = Settings()
