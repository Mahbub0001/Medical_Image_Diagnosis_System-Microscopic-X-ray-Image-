import base64
import os
import shutil
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from routers import run_image_routing_check
from inference import run_ensemble

app = FastAPI(title="BloodDetect AI ML Space")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
def home():
    return {"message": "BloodDetect AI Machine Learning Space is running"}

@app.post("/predict")
async def predict(
    disease_key: str = Form(...),
    file: UploadFile = File(...)
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG images are supported.")

    temp_image_path = TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    
    try:
        # Save image locally
        with open(temp_image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Domain routing check
        if disease_key in {"blood", "lung"}:
            is_valid_domain, domain_error = run_image_routing_check(str(temp_image_path), disease_key)
            if not is_valid_domain:
                raise HTTPException(status_code=400, detail={"message": "Invalid domain", "error": domain_error})

        # Run inference
        result = run_ensemble(str(temp_image_path), disease_key=disease_key)

        # Retrieve heatmap and convert to Base64
        heatmap_path = Path(result["heatmap_url"])
        if heatmap_path.exists():
            with open(heatmap_path, "rb") as image_file:
                base64_bytes = base64.b64encode(image_file.read())
                result["heatmap_base64"] = base64_bytes.decode("utf-8")
            
            # Clean up temp heatmap file to save space
            try:
                heatmap_path.unlink()
            except Exception:
                pass
        else:
            result["heatmap_base64"] = None

        # Clean up input temp image
        try:
            temp_image_path.unlink()
        except Exception:
            pass

        return result

    except HTTPException as he:
        # Clean up temp image
        try:
            temp_image_path.unlink()
        except Exception:
            pass
        raise he
    except Exception as e:
        # Clean up temp image
        try:
            temp_image_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
