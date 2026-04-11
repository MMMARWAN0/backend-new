from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app import models 
from app.database import get_db
from app.dependencies import get_current_user 

router = APIRouter(prefix="/sos", tags=["SOS Emergency"])

class SOSRequestCreate(BaseModel):
    user_id: int  
    location: str

class SOSRequestResponse(BaseModel):
    sos_id: int
    user_id: int
    location: str
    requested_at: datetime
    status_sos: str 
    class Config:
        from_attributes = True

@router.post("/send", response_model=SOSRequestResponse)
async def send_sos_signal(
    request: SOSRequestCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    if current_user["user_id"] != request.user_id:
        raise HTTPException(status_code=403, detail="لا يمكنك إرسال استغاثة بهوية شخص آخر")

    new_sos = models.sos_request.SoSRequest(
        user_id=request.user_id, 
        location=request.location,
        status_sos="Open"
    )
    db.add(new_sos)
    db.commit()
    db.refresh(new_sos)
    return new_sos


@router.get("/my-alerts/{user_id}", response_model=list[SOSRequestResponse])
def get_my_sos_history(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="غير مسموح لك بمشاهدة تاريخ استغاثات مستخدم آخر")

    return db.query(models.sos_request.SoSRequest).filter(
        models.sos_request.SoSRequest.user_id == user_id
    ).all()