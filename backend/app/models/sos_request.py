from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class SoSRequest(Base):
    __tablename__ = "sos_requests"

    sos_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    location = Column(String(255), nullable=False)
    requested_at = Column(DateTime, default=datetime.now) 
    status_sos = Column(String(50), default="Open") 