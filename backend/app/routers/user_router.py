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
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users Authentication"])



class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
    phone: Optional[str]
    national_id: Optional[str]
    age: Optional[int]
    role: str

    class Config:
        from_attributes = True

class UserLoginRequest(BaseModel): 
    national_id: str
    password: str

class UserRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    national_id: str
    age: int



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
        password_hash=get_password_hash(user_data.password),
        phone=user_data.phone,
        national_id=user_data.national_id,
        age=user_data.age
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.user_id}

@router.post("/login") 
def login_user(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.national_id == login_data.national_id).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    access_token = create_access_token(data={"sub": str(user.user_id), "name": user.name})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/all", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
   
    return db.query(User).all()

@router.get("/me/{user_id}", response_model=UserResponse)
def get_my_profile(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
   
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="غير مسموح لك بالوصول لبيانات مستخدم آخر")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/update/{user_id}", response_model=UserResponse)
def update_user_profile(
    user_id: int,
    update_data: UserUpdateRequest, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user) 
):
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="غير مسموح لك بتعديل بيانات مستخدم آخر")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    if update_data.name: user.name = update_data.name
    if update_data.phone: user.phone = update_data.phone
    if update_data.age: user.age = update_data.age
    if update_data.email: user.email = update_data.email

    db.commit()
    db.refresh(user)
    return user

@router.delete("/delete/{user_id}")
def delete_my_account(
    user_id: int,
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user) 
):
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="غير مسموح لك بحذف حساب مستخدم آخر")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db.delete(user)
    db.commit()
    return {"message": "Your account has been permanently deleted."}

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    return {"message": f"تم تسجيل الخروج بنجاح للمستخدم: {current_user['name']}"}