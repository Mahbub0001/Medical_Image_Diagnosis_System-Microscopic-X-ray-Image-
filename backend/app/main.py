from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .db.session import Base, engine
from .api.routes.auth import router as auth_router
from .api.routes.prediction import router as prediction_router
from .api.routes.admin import router as admin_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.report_dir).mkdir(parents=True, exist_ok=True)
Path(settings.heatmap_dir).mkdir(parents=True, exist_ok=True)

app.mount("/static/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/static/reports", StaticFiles(directory=settings.report_dir), name="reports")
app.mount("/static/heatmaps", StaticFiles(directory=settings.heatmap_dir), name="heatmaps")

app.include_router(auth_router)
app.include_router(prediction_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "BloodDetect AI API is running"}
