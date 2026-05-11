from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app import models 
from app.database import get_db
from app.dependencies import get_current_user 

router = APIRouter(prefix="/sos", tags=["SOS Emergency"])


class SOSRequestCreate(BaseModel):
    latitude: float 
    longitude: float  
    location_name: str = "Unknown Location" 

class SOSRequestResponse(BaseModel):
    sos_id: int
    user_id: int
    latitude: float
    longitude: float
    location_name: str
    requested_at: datetime
    status_sos: str 
    google_maps_url: str = None

    class Config:
        from_attributes = True

@router.post("/send", response_model=SOSRequestResponse)
async def send_sos_signal(
    request: SOSRequestCreate, 
    user_id: int = Header(...), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    if int(current_user["user_id"]) != int(user_id):
        raise HTTPException(status_code=403, detail="لا يمكنك إرسال استغاثة بهوية شخص آخر")

  
    new_sos = models.sos_request.SoSRequest(
        user_id=int(user_id), 
        latitude=request.latitude,
        longitude=request.longitude,
        location=request.location_name, 
        status_sos="Open"
    )
    
    db.add(new_sos)
    db.commit()
    db.refresh(new_sos)

    
    new_sos.google_maps_url = f"https://www.google.com/maps?q={request.latitude},{request.longitude}"
    
    return new_sos

@router.get("/my-alerts", response_model=list[SOSRequestResponse]) 
def get_my_sos_history(
    user_id: int = Header(...), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="غير مسموح لك بمشاهدة تاريخ استغاثات مستخدم آخر")

    alerts = db.query(models.sos_request.SoSRequest).filter(
        models.sos_request.SoSRequest.user_id == int(user_id)
    ).all()

    # إضافة لينكات الخرائط لكل التاريخ القديم في الرد
    for alert in alerts:
        alert.google_maps_url = f"https://www.google.com/maps?q={alert.latitude},{alert.longitude}"
    
    return alerts