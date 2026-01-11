"""
StepHistory - история вариантов для каждого шага workflow.

Позволяет:
- Хранить несколько вариантов для каждого шага
- Откатываться к предыдущим вариантам
- Отслеживать какой вариант выбран
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class StepHistory(Base):
    """История вариантов шагов workflow."""
    __tablename__ = "step_history"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    # Тип шага: story, description, prompt, image, scenario, video, audio
    step_type = Column(String(50), nullable=False, index=True)

    # Содержимое варианта (JSON)
    content = Column(JSON, nullable=False)

    # Выбран ли этот вариант как текущий
    is_selected = Column(Boolean, default=False, nullable=False)

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с Video
    video = relationship("Video", back_populates="step_history")

    def __repr__(self):
        return f"<StepHistory(id={self.id}, video_id={self.video_id}, step={self.step_type}, selected={self.is_selected})>"


# Маппинг step_type -> поле в Video
STEP_TO_VIDEO_FIELD = {
    "story": "story_data",
    "description": "description_data",
    "prompt": "prompt_data",
    "image": "image_url",
    "scenario": "scenario_data",
    "video": "video_url",
    "audio": "audio_url",
}

# Порядок шагов для Discover (scenario перед prompt для лучшей согласованности)
DISCOVER_STEPS = ["story", "description", "scenario", "prompt", "image", "video", "audio"]

# Порядок шагов для Remix
REMIX_STEPS = ["image", "video", "audio"]

# Зависимости: если изменился шаг X, нужно перегенерить шаги Y
STEP_DEPENDENCIES = {
    "story": ["description", "scenario", "prompt", "image", "video", "audio"],
    "description": ["scenario", "prompt", "image", "video", "audio"],
    "scenario": ["prompt", "image", "video", "audio"],  # scenario теперь влияет на prompt
    "prompt": ["image", "video", "audio"],
    "image": ["video", "audio"],
    "video": ["audio"],
    "audio": [],
}
