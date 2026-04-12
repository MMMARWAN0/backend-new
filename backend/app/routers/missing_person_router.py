from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
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

# --- 2. رفع بلاغ جديد (ID مبعوث في الـ Header) ---
@router.post("/report") # شيلنا الـ {user_id} من اللينك
async def report_missing_person(
    name: str = Form(...),
    age: int = Form(...),
    medical_notes: str = Form(None), 
    last_known_location: str = Form(...),
    image: UploadFile = File(...),
    user_id: int = Header(...), # سحب الـ ID من الهيدر (أنس هيبعته في الـ Interceptor)
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # التأكد من هوية المستخدم للأمان
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="ID المستخدم لا يطابق صاحب التوكن")

    # مسار الحفظ
    base_upload_dir = os.path.join(os.getcwd(), "backend", "uploads", "missing_persons")
    if not os.path.exists(base_upload_dir):
        os.makedirs(base_upload_dir, exist_ok=True)

    file_ext = image.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(base_upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_url = f"/static/missing_persons/{unique_filename}"

    new_person = MissingPerson(
        name=name,
        age=age,
        medical_notes=medical_notes,
        location=last_known_location,
        image_url=image_url,
        reported_by=int(user_id)
    )

    db.add(new_person)
    db.commit()
    db.refresh(new_person)
    return {"message": "تم تسجيل البلاغ بنجاح", "person_id": new_person.person_id}

# --- 3. جلب بلاغات المستخدم (ID مبعوث في الـ Header) ---
@router.get("/my-reports") # اللينك بقى نضيف مفيش فيه أرقام
def get_my_reports(
    user_id: int = Header(...), # سحب الـ ID من الهيدر
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # التحقق من الأمان
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="ID المستخدم لا يطابق صاحب التوكن")

    reports = db.query(MissingPerson).filter(MissingPerson.reported_by == int(user_id)).all()
    
    print(f"🔍 User {user_id} requested their reports via Header. Found: {len(reports)}")
    return reports