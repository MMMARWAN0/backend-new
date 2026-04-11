from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.missing_person import MissingPerson
from app.dependencies import get_current_user
import os
import uuid
import shutil

router = APIRouter(prefix="/missing-persons", tags=["Missing Persons"])

# --- 1. جلب كل المفقودين (لـ سكريبت الـ AI) ---
@router.get("/all")
def get_all_missing_persons(db: Session = Depends(get_db)):
    try:
        persons = db.query(MissingPerson).all()
        return persons
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

# --- 2. رفع بلاغ جديد ---
@router.post("/report/{user_id}")
async def report_missing_person(
    user_id: int,
    name: str = Form(...),
    age: int = Form(...),
    medical_notes: str = Form(None), 
    last_known_location: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # التأكد من صاحب التوكن
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="ID لا يطابق صاحب التوكن")

    # المسار اللي السيرفر هيحفظ فيه (المسار الحقيقي)
    # استخدمنا os.getcwd() عشان نضمن إن الفولدر يتكريت في مكان المشروع بالظبط
    base_upload_dir = os.path.join(os.getcwd(), "uploads", "missing_persons")
    if not os.path.exists(base_upload_dir):
        os.makedirs(base_upload_dir, exist_ok=True)

    file_ext = image.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(base_upload_dir, unique_filename)

    # حفظ الملف فعلياً
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # الرابط اللي هيتخزن في الداتابيز (عشان الـ AI والفرونت إند يشوفوه)
    # خزناه بـ "static" عشان الـ StaticFiles Mount اللي عملناه في الـ main يشوفه
    image_url = f"/static/missing_persons/{unique_filename}"

    new_person = MissingPerson(
        name=name,
        age=age,
        medical_notes=medical_notes,
        location=last_known_location,
        image_url=image_url,
        reported_by=int(user_id) # نضمن إنه Integer
    )

    db.add(new_person)
    db.commit()
    db.refresh(new_person)
    return {"message": "تم تسجيل البلاغ بنجاح", "person_id": new_person.person_id}

# --- 3. جلب بلاغاتي ---
@router.get("/my-reports/{user_id}")
def get_my_reports(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # التأكد من الأمان (تحويل الطرفين لـ int لضمان المقارنة)
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="ID لا يطابق صاحب التوكن")

    # فلترة مباشرة من الداتابيز (أسرع وأدق)
    reports = db.query(MissingPerson).filter(MissingPerson.reported_by == int(user_id)).all()
    
    print(f"🔍 User {user_id} requested their reports. Found: {len(reports)}")
    return reports