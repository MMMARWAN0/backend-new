from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class MissingPerson(Base):
    __tablename__ = "missing_persons"

    person_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)     
    governorate = Column(String(50), nullable=False) 
    medical_notes = Column(String(255), nullable=True)
    location = Column(String(255), nullable=False)   
    image_url = Column(String(255), nullable=False)
    reported_by = Column(Integer, ForeignKey("users.user_id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)