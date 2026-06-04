from pathlib import Path
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ...core.config import settings
from ...services.image_validation import validate_uploaded_image
from ...ml.inference import run_ensemble, clinical_suggestion
from ...ml.routers import run_image_routing_check
from ...services.report_service import generate_text_report
from ...services.cloudinary_service import upload_file_to_cloudinary
from ...db.session import SessionLocal
from ...db.models import Prediction
from typing import Optional

def format_db_url(path: Optional[str], default_prefix: str) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://") or path.startswith("/"):
        return path
    return f"{default_prefix}{path}"

router = APIRouter(prefix="/predict", tags=["prediction"])

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/analyze")
async def analyze_image(
    disease_key: str = Form(...),
    patient_name: str = Form("User"),
    file: UploadFile = File(...),
    user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG are supported.")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"

    content = await file.read()
    file_path.write_bytes(content)

    validation = validate_uploaded_image(str(file_path))
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"message": "Invalid image", "errors": validation["errors"]})

    # Domain validity routing check (blood smear / X-ray verification)
    if disease_key in {"blood", "lung"}:
        is_valid_domain, domain_error = run_image_routing_check(str(file_path), disease_key)
        if not is_valid_domain:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=domain_error)

    # Run the prediction
    prediction_result = run_ensemble(str(file_path), disease_key=disease_key)
    
    # Reconstruct local heatmap path
    local_heatmap = Path(settings.heatmap_dir) / Path(prediction_result["heatmap_url"]).name
    
    # Upload files (falls back to local static URL paths if Cloudinary is not configured)
    cloudinary_input_url = upload_file_to_cloudinary(str(file_path), folder="blooddetect/uploads")
    cloudinary_heatmap_url = upload_file_to_cloudinary(str(local_heatmap), folder="blooddetect/heatmaps")
    
    # Clean up local temporary files if they were successfully uploaded to Cloudinary
    if cloudinary_input_url.startswith("http"):
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
    if cloudinary_heatmap_url.startswith("http"):
        try:
            local_heatmap.unlink(missing_ok=True)
        except Exception:
            pass
            
    # Update prediction result URLs in response
    prediction_result["heatmap_url"] = cloudinary_heatmap_url
    
    # Save prediction to database in real-time
    db_prediction = Prediction(
        user_id=user_id,
        input_image_path=cloudinary_input_url,
        heatmap_path=cloudinary_heatmap_url,
        report_path=None,
        predicted_disease=prediction_result["predicted_disease"],
        predicted_class=prediction_result["predicted_class"],
        confidence=prediction_result["confidence"],
        certainty=prediction_result["certainty"],
        risk_level=prediction_result["risk_level"],
        notes=f"Patient: {patient_name}"
    )
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    
    # Set dynamically-generated PDF download endpoint path
    report_url_path = f"/predict/report/{db_prediction.id}"
    db_prediction.report_path = report_url_path
    db.commit()
    db.refresh(db_prediction)
    
    # Add database ID and final report URL to response
    prediction_result["report_url"] = report_url_path
    prediction_result["prediction_id"] = db_prediction.id
    prediction_result["created_at"] = db_prediction.created_at.isoformat() if db_prediction.created_at else None
    
    return prediction_result

@router.get("/history")
def get_prediction_history(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get prediction history, optionally filtered by user_id"""
    query = db.query(Prediction)
    if user_id:
        query = query.filter(Prediction.user_id == user_id)
    predictions = query.order_by(Prediction.created_at.desc()).all()
    
    result = []
    for pred in predictions:
        result.append({
            "id": pred.id,
            "user_id": pred.user_id,
            "predicted_disease": pred.predicted_disease,
            "predicted_class": pred.predicted_class,
            "confidence": pred.confidence,
            "certainty": pred.certainty,
            "risk_level": pred.risk_level,
            "notes": pred.notes,
            "created_at": pred.created_at.isoformat() if pred.created_at else None,
            "report_url": format_db_url(pred.report_path, "/static/reports/"),
            "heatmap_url": format_db_url(pred.heatmap_path, "/static/heatmaps/"),
        })
    return result

@router.get("/history/{prediction_id}")
def get_prediction_detail(prediction_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific prediction"""
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    return {
        "id": pred.id,
        "user_id": pred.user_id,
        "input_image_path": format_db_url(pred.input_image_path, "/static/uploads/"),
        "predicted_disease": pred.predicted_disease,
        "predicted_class": pred.predicted_class,
        "confidence": pred.confidence,
        "certainty": pred.certainty,
        "risk_level": pred.risk_level,
        "notes": pred.notes,
        "created_at": pred.created_at.isoformat() if pred.created_at else None,
        "report_url": format_db_url(pred.report_path, "/static/reports/"),
        "heatmap_url": format_db_url(pred.heatmap_path, "/static/heatmaps/"),
    }

def reconstruct_prediction_result(prediction: Prediction) -> dict:
    disease = prediction.predicted_disease.lower() if prediction.predicted_disease else ""
    predicted_class = prediction.predicted_class
    confidence = prediction.confidence
    
    # Class mapping matching our model registry display names
    class_map = {
        "malaria": ["Parasitized", "Uninfected"],
        "leukemia": ["Benign", "Early", "Pre", "Pro"],
        "anemia": ["Anemic", "Normal"],
        "lung": ["Normal", "Pneumonia", "Tuberculosis"]
    }
    
    classes = []
    for k, val in class_map.items():
        if k in disease:
            classes = val
            break
            
    probabilities = {}
    if classes:
        # Distribute probabilities: confidence for predicted class, and split remainder
        remaining_classes = [c for c in classes if c.lower() != predicted_class.lower()]
        actual_predicted_class = None
        for c in classes:
            if c.lower() == predicted_class.lower():
                actual_predicted_class = c
                break
        
        if actual_predicted_class:
            probabilities[actual_predicted_class] = confidence
            if remaining_classes:
                remaining_prob = (1.0 - confidence) / len(remaining_classes)
                for rc in remaining_classes:
                    probabilities[rc] = max(0.0, remaining_prob)
        else:
            probabilities[predicted_class] = confidence
    else:
        probabilities[predicted_class] = confidence

    return {
        "predicted_disease": prediction.predicted_disease,
        "predicted_class": prediction.predicted_class,
        "confidence": prediction.confidence,
        "certainty": prediction.certainty,
        "risk_level": prediction.risk_level,
        "probabilities": probabilities,
        "suggestion": clinical_suggestion(prediction.predicted_class, prediction.risk_level)
    }

def delete_temp_file(path: str):
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass

@router.get("/report/{prediction_id}")
def download_report(prediction_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Report not found")
        
    patient_name = "User"
    if pred.notes and pred.notes.startswith("Patient: "):
        patient_name = pred.notes.replace("Patient: ", "")
    elif pred.notes:
        patient_name = pred.notes
        
    reconstructed = reconstruct_prediction_result(pred)
    
    # Generate the PDF file dynamically
    report_path = generate_text_report(reconstructed, patient_name=patient_name)
    
    # Schedule deletion of the PDF file after sending
    background_tasks.add_task(delete_temp_file, report_path)
    
    headers = {
        "Content-Disposition": f'inline; filename="report_{prediction_id}.pdf"'
    }
    
    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        headers=headers
    )
