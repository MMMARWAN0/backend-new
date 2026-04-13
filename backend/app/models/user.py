from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(String(50), default="user")
    
    national_id = Column(String(20), unique=True, nullable=True)
    age = Column(Integer, nullable=True)
    
  
    profile_image_url = Column(String(255), nullable=True) 
    id_front_url = Column(String(255), nullable=True)
    id_back_url = Column(String(255), nullable=True)
    
    is_verified = Column(Boolean, default=False)