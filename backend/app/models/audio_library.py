"""Audio Library model — per-workspace collection of generated audio tracks."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from datetime import datetime

from app.db.base import Base


class AudioLibrary(Base):
    """Per-workspace audio library. Stores generated SFX and music tracks."""
    __tablename__ = "audio_library"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source tracking
    source_type = Column(String(20), nullable=False)  # 'sfx' | 'music'
    source_discover_project_id = Column(
        Integer,
        ForeignKey("discover_projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Audio file
    file_path = Column(String(500), nullable=False)       # trimmed hook
    track_path = Column(String(500), nullable=True)       # full original track (for re-trimming)
    hook_start_ms = Column(Integer, nullable=True)        # verified hook start in full track
    hook_end_ms = Column(Integer, nullable=True)          # verified hook end in full track
    file_url = Column(String(500), nullable=True)
    duration_ms = Column(Integer, nullable=False)

    # Metadata
    prompt = Column(Text, nullable=True)
    mood = Column(String(20), nullable=True)  # energetic|calm|dramatic|playful|dark|neutral

    # Usage stats
    use_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audio_library_workspace_mood", "workspace_id", "mood"),
        Index("ix_audio_library_workspace_created", "workspace_id", "created_at"),
    )
