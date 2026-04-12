from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app import models 
from app.database import get_db
from app.dependencies import get_current_user 

router = APIRouter(prefix="/sos", tags=["SOS Emergency"])


class SOSRequestCreate(BaseModel):
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
    user_id: int = Header(...), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
  
    if int(current_user["user_id"]) != int(user_id):
        raise HTTPException(status_code=403, detail="لا يمكنك إرسال استغاثة بهوية شخص آخر")

    new_sos = models.sos_request.SoSRequest(
        user_id=int(user_id), 
        location=request.location,
        status_sos="Open"
    )
    db.add(new_sos)
    db.commit()
    db.refresh(new_sos)
    return new_sos


@router.get("/my-alerts", response_model=list[SOSRequestResponse]) 
def get_my_sos_history(
    user_id: int = Header(...), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
   
    if int(user_id) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="غير مسموح لك بمشاهدة تاريخ استغاثات مستخدم آخر")

    return db.query(models.sos_request.SoSRequest).filter(
        models.sos_request.SoSRequest.user_id == int(user_id)
    ).all()