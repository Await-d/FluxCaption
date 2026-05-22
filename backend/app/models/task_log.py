"""
Task Log model for storing job execution logs.

Allows viewing historical logs for completed tasks.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TaskLog(BaseModel):
    """
    Task execution log entries.

    Stores detailed log information for each job, allowing historical log viewing.
    """

    __tablename__ = "task_log"

    # Job ID this log belongs to
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Log timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Current phase: init | pull | extract | asr | mt | post | writeback | completed
    phase: Mapped[str] = mapped_column(String(16), nullable=False)

    # Status message
    status: Mapped[str] = mapped_column(Text, nullable=False)

    # Progress percentage (0-100)
    progress: Mapped[float] = mapped_column(nullable=False, default=0.0)

    # Completed items count
    completed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Total items count
    total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional data (JSON)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_task_log_job_timestamp", "job_id", "timestamp"),
        Index("idx_task_log_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<TaskLog(job_id={self.job_id}, phase={self.phase}, "
            f"progress={self.progress:.1f}%, timestamp={self.timestamp})>"
        )
