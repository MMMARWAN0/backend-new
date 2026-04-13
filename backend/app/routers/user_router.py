import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Header, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from jose import jwt
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
    profile_image_url: Optional[str] = None  
    

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
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    national_id: str = Form(...),
    age: int = Form(...),
    id_front: UploadFile = File(...),   
    id_back: UploadFile = File(...),    
    profile_image: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
  
    existing_user = db.query(User).filter(
        (User.national_id == national_id) | (User.email == email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="المستخدم موجود بالفعل!")

   
    base_dir = os.path.join(os.getcwd(), "backend", "uploads")
    id_dir = os.path.join(base_dir, "national_ids")
    profile_dir = os.path.join(base_dir, "profiles")
    
    os.makedirs(id_dir, exist_ok=True)
    os.makedirs(profile_dir, exist_ok=True)

  
    front_filename = f"{national_id}_front.{id_front.filename.split('.')[-1]}"
    with open(os.path.join(id_dir, front_filename), "wb") as buffer:
        shutil.copyfileobj(id_front.file, buffer)

    back_filename = f"{national_id}_back.{id_back.filename.split('.')[-1]}"
    with open(os.path.join(id_dir, back_filename), "wb") as buffer:
        shutil.copyfileobj(id_back.file, buffer)

  
    profile_ext = profile_image.filename.split(".")[-1]
    profile_filename = f"{national_id}_profile_{uuid.uuid4().hex[:6]}.{profile_ext}"
    with open(os.path.join(profile_dir, profile_filename), "wb") as buffer:
        shutil.copyfileobj(profile_image.file, buffer)

   
    new_user = User(
        name=name,
        email=email,
        password_hash=get_password_hash(password),
        phone=phone,
        national_id=national_id,
        age=age,
        id_front_url=f"/static/national_ids/{front_filename}",
        id_back_url=f"/static/national_ids/{back_filename}",
        profile_image_url=f"/static/profiles/{profile_filename}" 
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "تم التسجيل بنجاح  ", "user_id": new_user.user_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "تم التسجيل بنجاح مع صور البطاقة", "user_id": new_user.user_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطأ في حفظ البيانات: {str(e)}")

@router.post("/login") 
def login_user(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.national_id == login_data.national_id).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    
    access_token = create_access_token(data={"sub": str(user.user_id), "name": user.name})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id 
    }


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    user_id: int = Header(...), 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user 

@router.put("/update", response_model=UserResponse)
def update_user_profile(
    update_data: UserUpdateRequest, 
    user_id: int = Header(...), 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user) 
):
    if int(user_id) != int(current_user["user_id"]):
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


@router.delete("/delete")
def delete_my_account(
    user_id: int = Header(...), 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user) 
):
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="غير مسموح لك بحذف حساب مستخدم آخر")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
    db.delete(user)
    db.commit()
    return {"message": "Your account has been permanently deleted."}

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    return {"message": f"تم تسجيل الخروج بنجاح للمستخدم: {current_user['name']}"}