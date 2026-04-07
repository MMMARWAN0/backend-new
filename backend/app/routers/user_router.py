from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.database import get_db
from app.models.user import User
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm

SECRET_KEY = "marwan_secret_key_for_missing_person_app" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/users", tags=["Users Authentication"])


def get_password_hash(password: str):
    
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8') 

def verify_password(plain_password: str, hashed_password: str):
    
    password_byte = plain_password.encode('utf-8')
    hashed_byte = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte, hashed_byte)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class UserRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    national_id: str
    age: int

class UserLoginRequest(BaseModel):
    national_id: str
    password: str



@router.post("/register")
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.national_id == user_data.national_id) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists!")

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password), # تشفير الباسورد قبل الحفظ
        phone=user_data.phone,
        national_id=user_data.national_id,
        age=user_data.age
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.user_id}

@router.post("/login")
def login_user(login_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
  
    user = db.query(User).filter(User.national_id == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    access_token = create_access_token(data={"sub": str(user.user_id), "name": user.name})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/all")
def get_all_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        
        return [
            {
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "national_id": u.national_id,
                "age": u.age,
                "role": u.role,
                "is_verified": u.is_verified,
                "id_front_url": u.id_front_url,
                "id_back_url": u.id_back_url,
                "selfie_url": u.selfie_url,
               
            } for u in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))