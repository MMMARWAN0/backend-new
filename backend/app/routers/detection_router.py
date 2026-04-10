from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.detection import Detection
from app.models.missing_person import MissingPerson
import shutil
import uuid
import os

from app.dependencies import get_current_user

router = APIRouter(prefix="/detections", tags=["AI Detections"])

@router.post("/match")
def register_ai_detection(
    person_id: int = Form(...), 
    confidence_level: float = Form(...), 
    location: str = Form(...), 
    camera_id: int = Form(None), 
    image: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
  
    upload_dir = "uploads/detections"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_ext = image.filename.split(".")[-1]
    unique_filename = f"ai_match_{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    image_url = f"/static/detections/{unique_filename}"

    new_detection = Detection(
        person_id=person_id,
        camera_id=camera_id,
        confidence_level=confidence_level,
        detected_image_url=image_url,
        location=location
    )
    
    try:
        db.add(new_detection)
        db.commit()
        db.refresh(new_detection)

        return {
            "message": "AI Match recorded successfully!",
            "detection_id": new_detection.detection_id,
            "person_id": person_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


@router.get("/notifications/{user_id}")
def get_user_notifications(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) 
):
   
    if user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="غير مسموح لك بالوصول لإشعارات مستخدم آخر!"
        )

    
    notifications = db.query(Detection, MissingPerson.name)\
        .join(MissingPerson, Detection.person_id == MissingPerson.person_id)\
        .filter(MissingPerson.reported_by == user_id)\
        .order_by(Detection.detected_at.desc())\
        .all()
    
    result = []
    for det, person_name in notifications:
        result.append({
            "detection_id": det.detection_id,
            "person_id": det.person_id,
            "person_name": person_name, 
            "confidence_level": det.confidence_level, 
            "location": det.location, 
            "detected_image_url": det.detected_image_url, 
            "detected_at": det.detected_at 
        })
        
    return result