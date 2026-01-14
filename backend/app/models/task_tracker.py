"""
TaskTracker - отслеживание внешних async задач (PiAPI: Suno, Kling).

Обеспечивает идемпотентность генерации:
- Хранит external_task_id для каждой генерации
- Позволяет проверить статус перед созданием нового task
- Поддерживает resume после page refresh
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.db.base import Base


class TaskStatus(str, Enum):
    """Статусы внешней задачи."""
    PENDING = "pending"      # Task created, not yet sent to provider
    RUNNING = "running"      # Sent to provider, awaiting result
    COMPLETED = "completed"  # Provider returned success
    FAILED = "failed"        # Provider returned error or timeout


class TaskTracker(Base):
    """Отслеживание внешних async задач."""
    __tablename__ = "task_tracker"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    # Какой шаг генерируется
    step_type = Column(String(50), nullable=False, index=True)  # scenario, image, video, audio

    # Провайдер и его task_id
    provider = Column(String(50), nullable=False)  # suno, kling, openai, etc.
    external_task_id = Column(String(255), nullable=True, index=True)  # PiAPI task_id

    # Статус
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Результат (кэш ответа от провайдера)
    result = Column(JSON, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # When sent to provider
    completed_at = Column(DateTime, nullable=True)  # When provider responded

    # Связь с video
    video = relationship("Video", back_populates="task_trackers")

    def __repr__(self):
        return f"<TaskTracker(id={self.id}, video_id={self.video_id}, step={self.step_type}, provider={self.provider}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Активна ли задача (можно ли запрашивать статус)."""
        return self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]

    @property
    def is_terminal(self) -> bool:
        """Завершена ли задача (успешно или с ошибкой)."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
