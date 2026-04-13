from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.database import Base
from datetime import datetime

class MissingPerson(Base):
    __tablename__ = "missing_persons"

    person_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20))
    location = Column(String(255)) 
    medical_notes = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    status = Column(String(50), default="Active")
    date_reported = Column(DateTime, default=datetime.utcnow)
    reported_by = Column(Integer, ForeignKey("users.user_id"))