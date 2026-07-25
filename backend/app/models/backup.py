from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class BackupLog(Base):
    """Backup job record."""

    __tablename__ = "backup_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(500), comment="Backup file path")
    file_size = Column(Integer, comment="File size in bytes")
    created_at = Column(DateTime, default=datetime.now)
