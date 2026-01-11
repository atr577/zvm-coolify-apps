"""
StepHistory - история вариантов для каждого шага workflow.

Позволяет:
- Хранить несколько вариантов для каждого шага
- Откатываться к предыдущим вариантам
- Отслеживать какой вариант выбран
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class StepHistory(Base):
    """История вариантов шагов workflow."""
    __tablename__ = "step_history"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    # Тип шага: scenario, image, video, audio
    step_type = Column(String(50), nullable=False, index=True)

    # Содержимое варианта (JSON)
    content = Column(JSON, nullable=False)

    # Выбран ли этот вариант как текущий
    is_selected = Column(Boolean, default=False, nullable=False)

    # Status tracking (NEW)
    status = Column(String(20), default="pending", nullable=True)  # pending, success, failed
    error_message = Column(Text, nullable=True)

    # Metrics (NEW)
    generation_time_seconds = Column(Float, nullable=True)

    # Lineage for regenerate with feedback (NEW)
    parent_id = Column(Integer, ForeignKey("step_history.id"), nullable=True)
    feedback = Column(Text, nullable=True)

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    video = relationship("Video", back_populates="step_history")
    parent = relationship("StepHistory", remote_side=[id], backref="children")

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

# Порядок шагов для Discover (NEW: simplified workflow)
# scenario generates image_prompt + motion_prompt from story_template + content_variables
DISCOVER_STEPS = ["scenario", "image", "video", "audio"]

# Порядок шагов для Remix
REMIX_STEPS = ["image", "video", "audio"]

# Зависимости: если изменился шаг X, нужно перегенерить шаги Y
STEP_DEPENDENCIES = {
    "scenario": ["image", "video", "audio"],
    "image": ["video", "audio"],
    "video": ["audio"],
    "audio": [],
}
