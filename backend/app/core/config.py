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

    # === AI Providers ===

    # OpenAI (for LLM - gpt-4o-mini)
    OPENAI_API_KEY: str = ""  # Required for LLM calls
    OPENAI_AUDIO_MODEL: str = "gpt-4o-audio-preview"  # Model for audio analysis

    # fal.ai (for image/video/music generation)
    FAL_KEY: str = ""  # Required for fal.ai services

    # Модели
    LLM_MODEL: str = "gpt-4o-mini"  # gpt-4o-mini, gpt-4o
    IMAGE_MODEL: str = "fal-ai/nano-banana-pro"  # fal.ai model
    VIDEO_MODEL: str = "fal-ai/veo3.1/image-to-video"  # fal.ai model
    MUSIC_MODEL: str = "fal-ai/lyria2"  # fal.ai model

    # === Legacy (deprecated - will be removed) ===
    PIAPI_KEY: str = ""  # Deprecated: use OPENAI_API_KEY + FAL_KEY
    PIAPI_LLM_URL: str = "https://api.piapi.ai/v1"  # Deprecated
    PIAPI_TASK_URL: str = "https://api.piapi.ai/api/v1"  # Deprecated
    AIMLAPI_KEY: str = ""  # Deprecated
    GPT_MODEL: str = ""  # Deprecated: use LLM_MODEL
    KLING_MODEL: str = ""  # Deprecated: use VIDEO_MODEL

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
