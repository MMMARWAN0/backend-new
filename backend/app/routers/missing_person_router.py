from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.missing_person import MissingPerson
from app.dependencies import get_current_user
import os
import uuid
import shutil

router = APIRouter(prefix="/missing-persons", tags=["Missing Persons"])


@router.post("/report/{user_id}")
async def report_missing_person(
    user_id: int,
    name: str = Form(...),
    age: int = Form(...),
    description: str = Form(...),
    last_known_location: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
   
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="غير مسموح لك برفع بلاغ بهوية مستخدم آخر")

    # حفظ الصورة
    upload_dir = "uploads/missing_persons"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_ext = image.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_url = f"/static/missing_persons/{unique_filename}"

    
    new_person = MissingPerson(
        name=name,
        age=age,
        description=description,
        last_known_location=last_known_location,
        image_url=image_url,
        reported_by=user_id 
    )

    db.add(new_person)
    db.commit()
    db.refresh(new_person)

    return {"message": "تم تسجيل البلاغ بنجاح", "person_id": new_person.person_id}


@router.get("/my-reports/{user_id}")
def get_my_reports(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # التحقق المزدوج
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="غير مسموح لك بمشاهدة بلاغات مستخدم آخر")

    reports = db.query(MissingPerson).filter(MissingPerson.reported_by == user_id).all()
    return reports