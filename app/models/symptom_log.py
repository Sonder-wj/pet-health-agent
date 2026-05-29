from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class SymptomLog(Base):
    __tablename__ = "symptom_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(36), nullable=False, index=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
