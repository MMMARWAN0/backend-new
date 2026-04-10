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
    
    user_id_from_token = current_user["user_id"]


    if user_id_from_token != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مسموح لك بإرسال استغاثة بهوية شخص آخر!"
        )

    new_sos = models.sos_request.SoSRequest(
        user_id=request.user_id, 
        location=request.location,
        status_sos="Open"
    )

    try:
        db.add(new_sos)
        db.commit()
        db.refresh(new_sos)
        
        print(f"🚨 [SOS RECEIVED] Authorized User {request.user_id} ({current_user['name']}) is in DANGER!")
        return new_sos
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

@router.get("/my-alerts", response_model=list[SOSRequestResponse])
def get_my_sos_history(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) 
):
    
    return db.query(models.sos_request.SoSRequest).filter(
        models.sos_request.SoSRequest.user_id == current_user["user_id"]
    ).all()