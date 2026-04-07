from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app import models  
from app.database import get_db

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.routers.user_router import SECRET_KEY, ALGORITHM 

router = APIRouter(prefix="/sos", tags=["SOS Emergency"]) 


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid Token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


class SOSRequestCreate(BaseModel):
    location: str

class SOSRequestResponse(BaseModel):
    sos_id: int
    user_id: int
    location: str
    requested_at: datetime
    status: str
    class Config:
        from_attributes = True


@router.post("/send", response_model=SOSRequestResponse)
async def send_sos_signal(
    request: SOSRequestCreate, 
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user) 
):
    
    new_sos = models.sos_request.SoSRequest(
        user_id=int(current_user_id), 
        location=request.location,
        status="Open"
    )

    try:
        db.add(new_sos)
        db.commit()
        db.refresh(new_sos)
        
        print(f"🚨 [SOS RECEIVED] Authorized User {current_user_id} is in DANGER!")
        return new_sos
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")