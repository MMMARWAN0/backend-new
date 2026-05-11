from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.missing_person import MissingPerson
from app.dependencies import get_current_user
import os
import uuid
import shutil
from enum import Enum
import numpy as np
from deepface import DeepFace

class GenderEnum(str, Enum):
    male = "ذكر"
    female = "أنثى"

class StatusEnum(str, Enum):
    searching = "قيد البحث"
    found = "تم العثور عليه"
    closed = "مغلق"

router = APIRouter(prefix="/missing-persons", tags=["Missing Persons"])

@router.get("/all")
def get_all_missing_persons(db: Session = Depends(get_db)):
    try:
        persons = db.query(MissingPerson).all()
        return persons
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

@router.post("/report") 
async def report_missing_person(
    name: str = Form(...),
    age: int = Form(...),
    gender: GenderEnum = Form(...),     
    governorate: str = Form(...), 
    medical_notes: str = Form(None), 
    last_known_location: str = Form(...),
    image: UploadFile = File(...),
    user_id: int = Header(...), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Unauthorized user ID")

    base_upload_dir = os.path.join(os.getcwd(), "uploads", "missing_persons")
    os.makedirs(base_upload_dir, exist_ok=True)

    file_ext = image.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(base_upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_url = f"static/missing_persons/{unique_filename}"

    new_person = MissingPerson(
        name=name,
        age=age,
        gender=gender.value, 
        governorate=governorate,
        medical_notes=medical_notes,
        location=last_known_location,
        image_url=image_url,
        reported_by=int(user_id),
        status=StatusEnum.searching.value  
    )

    db.add(new_person)
    db.commit()
    db.refresh(new_person)
    return {"message": "تم تسجيل البلاغ بنجاح", "person_id": new_person.person_id}

@router.get("/my-reports") 
def get_my_reports(
    user_id: int = Header(...), 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="ID المستخدم لا يطابق صاحب التوكن")

    reports = db.query(MissingPerson).filter(MissingPerson.reported_by == int(user_id)).all()
    return reports

@router.post("/search-by-image")
async def search_by_image(
    location: str = Form(...),          
    notes: str = Form(None),          
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    temp_path = f"temp_search_{uuid.uuid4()}.jpg"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    try:
        # 1. تحليل الصورة المرفوعة لاستخراج البصمة الوجهية
        current_face_objs = DeepFace.represent(
            img_path=temp_path, 
            model_name="VGG-Face",
            enforce_detection=False, 
            detector_backend="opencv",
            align=True 
        )
        current_embedding = np.array(current_face_objs[0]["embedding"])

        all_persons = db.query(MissingPerson).all()
        matches = []
        
        # المسار الأساسي للمشروع
        base_dir = os.getcwd()

        for person in all_persons:
            # استخراج اسم الملف من الرابط المخزن في الداتابيز
            image_filename = os.path.basename(person.image_url)
            # بناء المسار المحلي للصورة لمقارنتها
            local_path = os.path.join(base_dir, "uploads", "missing_persons", image_filename)

            if os.path.exists(local_path):
                try:
                    stored_face_objs = DeepFace.represent(
                        img_path=local_path, 
                        model_name="VGG-Face",
                        enforce_detection=False
                    )
                    stored_embedding = np.array(stored_face_objs[0]["embedding"])

                    # حساب الـ Cosine Similarity (نفس الـ Logic بتاعك)
                    dist = 1 - (np.dot(current_embedding, stored_embedding) / 
                               (np.linalg.norm(current_embedding) * np.linalg.norm(stored_embedding)))
                    
                    confidence = round((1 - dist) * 100, 2)

                    # عتبة الثقة 35% لضمان ظهور نتائج محتملة
                    if confidence > 35:  
                        matches.append({
                            "person": person,
                            "match_percentage": confidence,
                            "reported_location": location, 
                            "user_notes": notes            
                        })
                except Exception as e:
                    print(f"❌ خطأ في معالجة الصورة {image_filename}: {e}")
                    continue
            else:
                print(f"⚠️ الصورة غير موجودة في المسار: {local_path}")

        # ترتيب النتائج وناخد أعلى 5
        matches = sorted(matches, key=lambda x: x["match_percentage"], reverse=True)[:5]

        if not matches:
            return {"message": "لم يتم العثور على أي شخص يشبه هذه الصورة في قاعدة البيانات", "matches": []}

        return {"matches": matches}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)