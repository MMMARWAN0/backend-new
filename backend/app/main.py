from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
import os
from . import models
from app.models.user import User
from app.models.missing_person import MissingPerson
from app.models.camera import Camera
from app.models.detection import Detection
from app.models.sos_request import SoSRequest
from app.routers import user_router, missing_person_router
from app.routers import user_router, missing_person_router, detection_router
from .routers import sos_router
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Missing Person Detection System")


BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
PROJECT_DIR = os.path.dirname(BASE_DIR) 
UPLOADS_DIR = os.path.join(PROJECT_DIR, "uploads")

UPLOAD_FOLDERS = [
    os.path.join(UPLOADS_DIR, "verifications"),
    os.path.join(UPLOADS_DIR, "missing_persons"),
    os.path.join(UPLOADS_DIR, "detections")
]

for folder in UPLOAD_FOLDERS:
    os.makedirs(folder, exist_ok=True)


app.mount("/static", StaticFiles(directory=UPLOADS_DIR), name="static")


app.include_router(user_router.router)
app.include_router(missing_person_router.router)
app.include_router(detection_router.router)
app.include_router(sos_router.router, prefix="/sos", tags=["SOS Alerts"])
@app.get("/")
def home():
    return {"message": "System is Up and Running!"}



