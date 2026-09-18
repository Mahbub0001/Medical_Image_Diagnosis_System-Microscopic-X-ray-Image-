from pathlib import Path
import uuid
import gc
import re
import httpx
import base64
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ...core.config import settings
from ...services.image_validation import validate_uploaded_image, resize_image_in_place
from ...services.report_service import generate_text_report, generate_combined_report
from ...services.cloudinary_service import upload_file_to_cloudinary
from ...db.session import SessionLocal
from ...db.models import Prediction
from typing import Optional, Dict

def format_db_url(path: Optional[str], default_prefix: str) -> Optional[str]:
    if not path:
        return None
    url = path
    if not (path.startswith("http://") or path.startswith("https://") or path.startswith("/")):
        url = f"{default_prefix}{path}"
        
    # Auto-inject quality and format optimization for Cloudinary image assets
    if "res.cloudinary.com" in url and "/upload/" in url and not url.lower().endswith(".pdf"):
        if "q_auto,f_auto" not in url:
            url = url.replace("/upload/", "/upload/q_auto,f_auto/")
            
    return url

router = APIRouter(prefix="/predict", tags=["prediction"])

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def background_sync_single(pred_id: int, file_path_str: str, heatmap_path_str: Optional[str]):
    """Uploads files to Cloudinary in background and updates DB with permanent cloud URLs."""
    try:
        c_in = upload_file_to_cloudinary(file_path_str, "biolens/uploads")
        c_hm = upload_file_to_cloudinary(heatmap_path_str, "biolens/heatmaps") if heatmap_path_str else None
        
        db = SessionLocal()
        try:
            row = db.query(Prediction).filter(Prediction.id == pred_id).first()
            if row:
                if c_in and c_in.startswith("http"):
                    row.input_image_path = c_in
                if c_hm and c_hm.startswith("http"):
                    row.heatmap_path = c_hm
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Background cloud sync error for #{pred_id}: {e}")


def background_sync_batch(items: list):
    """Uploads batch of comprehensive panel files to Cloudinary in background thread pool."""
    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = []
            for it in items:
                f_in = pool.submit(upload_file_to_cloudinary, it["file_path"], "biolens/uploads")
                f_hm = pool.submit(upload_file_to_cloudinary, it["local_heatmap"], "biolens/heatmaps") if it.get("local_heatmap") else None
                futs.append((it["pred_id"], f_in, f_hm))
            
            db = SessionLocal()
            try:
                for pid, f_in, f_hm in futs:
                    c_in = f_in.result()
                    c_hm = f_hm.result() if f_hm else None
                    row = db.query(Prediction).filter(Prediction.id == pid).first()
                    if row:
                        if c_in and c_in.startswith("http"):
                            row.input_image_path = c_in
                        if c_hm and c_hm.startswith("http"):
                            row.heatmap_path = c_hm
                db.commit()
            finally:
                db.close()
    except Exception as e:
        print(f"Background batch cloud sync error: {e}")


@router.post("/analyze")
async def analyze_image(
    background_tasks: BackgroundTasks,
    disease_key: str = Form(...),
    patient_name: str = Form("User"),
    phone_number: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    phone_clean = phone_number.strip() if phone_number else ""
    if phone_clean:
        if not re.match(r"^01\d{9}$", phone_clean):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number. It must start with '01' and be exactly 11 digits (e.g. 01712345678)."
            )

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

    # Resize large images to max 1024px to save storage/bandwidth on upload
    resize_image_in_place(str(file_path), max_size=1024)

    # 1. Hugging Face Space Integration Path
    if settings.hf_space_url:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "image/jpeg")}
                data = {"disease_key": disease_key}
                
                # Send request to Hugging Face Space
                response = httpx.post(
                    f"{settings.hf_space_url.rstrip('/')}/predict",
                    files=files,
                    data=data,
                    timeout=60.0
                )
                
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    detail_msg = error_data.get("detail", {}).get("error") or error_data.get("detail") or "HF Space error."
                except Exception:
                    detail_msg = response.text
                raise HTTPException(status_code=response.status_code, detail=detail_msg)
                
            prediction_result = response.json()
            
            # Decode the base64 heatmap and save to local disk
            base64_heatmap = prediction_result.pop("heatmap_base64", None)
            local_heatmap = Path(settings.heatmap_dir) / f"{uuid.uuid4().hex}.png"
            local_heatmap.parent.mkdir(parents=True, exist_ok=True)
            
            if base64_heatmap:
                with open(local_heatmap, "wb") as fh:
                    fh.write(base64.b64decode(base64_heatmap))
            else:
                local_heatmap = None
                
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Failed to communicate with Hugging Face Space: {exc}")
            
    # 2. Local Fallback Path (Runs PyTorch models locally)
    else:
        # Import heavy packages locally to prevent startup OOM in lightweight environments
        from ...ml.routers import run_image_routing_check
        from ...ml.inference import run_ensemble

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
    
    local_input_url = f"/static/uploads/{file_path.name}"
    local_heatmap_url = f"/static/heatmaps/{local_heatmap.name}" if local_heatmap else None
    prediction_result["heatmap_url"] = local_heatmap_url
    
    # Save prediction to database in single efficient commit
    db_prediction = Prediction(
        user_id=user_id,
        input_image_path=local_input_url,
        heatmap_path=local_heatmap_url,
        report_path=None,
        predicted_disease=prediction_result["predicted_disease"],
        predicted_class=prediction_result["predicted_class"],
        confidence=prediction_result["confidence"],
        certainty=prediction_result["certainty"],
        risk_level=prediction_result["risk_level"],
        patient_name=patient_name,
        phone_number=phone_number,
        notes=f"Patient: {patient_name} | Phone: {phone_number or 'N/A'}"
    )
    db.add(db_prediction)
    db.flush()  # Populates ID in 1 step without separate network commit
    
    report_url_path = f"/predict/report/{db_prediction.id}"
    db_prediction.report_path = report_url_path
    db.commit()
    db.refresh(db_prediction)
    
    # Add database ID and final report URL to response
    prediction_result["report_url"] = report_url_path
    prediction_result["prediction_id"] = db_prediction.id
    prediction_result["created_at"] = db_prediction.created_at.isoformat() if db_prediction.created_at else None
    
    # Schedule background Cloudinary upload without delaying the HTTP response
    background_tasks.add_task(
        background_sync_single,
        db_prediction.id,
        str(file_path),
        str(local_heatmap) if local_heatmap and local_heatmap.exists() else None
    )
    
    # Collect unused memory from inference
    gc.collect()
    
    return prediction_result


# ---------------------------------------------------------------------------
# Comprehensive Blood Panel — multi-test endpoint
# ---------------------------------------------------------------------------

ANALYSIS_ORDER = [
    ("anemia",   "Anemia"),
    ("malaria",  "Malaria"),
    ("leukemia", "Leukemia"),
]

@router.post("/analyze-comprehensive")
async def analyze_comprehensive(
    background_tasks: BackgroundTasks,
    patient_name:   str = Form("User"),
    phone_number:   Optional[str] = Form(None),
    user_id:        Optional[int] = Form(None),
    anemia_image:   Optional[UploadFile] = File(None),
    malaria_image:  Optional[UploadFile] = File(None),
    leukemia_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    phone_clean = phone_number.strip() if phone_number else ""
    if phone_clean:
        if not re.match(r"^01\d{9}$", phone_clean):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number. It must start with '01' and be exactly 11 digits (e.g. 01712345678)."
            )

    uploaded_files: dict[str, UploadFile] = {
        "anemia":   anemia_image,
        "malaria":  malaria_image,
        "leukemia": leukemia_image,
    }
    # Filter to only the slots the user actually filled
    active = {k: v for k, v in uploaded_files.items() if v is not None}

    if not active:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one blood smear image.",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    findings      = []   # list of enriched result dicts
    prediction_ids = []  # DB IDs of saved sub-results

    # Respect a fixed display order regardless of form submission order
    ordered_active = [
        (slot_key, label)
        for slot_key, label in ANALYSIS_ORDER
        if slot_key in active
    ]

    # Phase 1: Image Validation & AI Inference for all selected tests
    inferred_items = []
    from ...ml.routers   import run_image_routing_check
    from ...ml.inference import run_ensemble
    from ...services.image_validation import validate_uploaded_image, resize_image_in_place

    for slot_key, disease_label in ordered_active:
        upload_file = active[slot_key]
        suffix = Path(upload_file.filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            raise HTTPException(
                status_code=400,
                detail=f"{disease_label} image: Only JPG, JPEG, and PNG are supported.",
            )

        file_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
        content = await upload_file.read()
        file_path.write_bytes(content)

        validation = validate_uploaded_image(str(file_path))
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={"message": f"{disease_label} image is invalid", "errors": validation["errors"]},
            )
        resize_image_in_place(str(file_path), max_size=1024)

        is_valid, domain_error = run_image_routing_check(str(file_path), "blood")
        if not is_valid:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"{disease_label}: {domain_error}",
            )

        prediction_result = run_ensemble(str(file_path), disease_key="blood")
        heatmap_name      = Path(prediction_result.get("heatmap_url", "")).name
        local_heatmap     = Path(settings.heatmap_dir) / heatmap_name if heatmap_name else None

        # --- Strict Disease Slot Matching Validation ---
        pred_disease = prediction_result.get("predicted_disease", "")
        if pred_disease.lower() != slot_key.lower():
            # Clean up all created files in this request before aborting
            try:
                file_path.unlink(missing_ok=True)
                for it in inferred_items:
                    it["file_path"].unlink(missing_ok=True)
                    if it.get("local_heatmap") and it["local_heatmap"].exists():
                        it["local_heatmap"].unlink(missing_ok=True)
                if local_heatmap and local_heatmap.exists():
                    local_heatmap.unlink(missing_ok=True)
            except Exception:
                pass

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Slot Mismatch in '{disease_label}' Section: The uploaded image was identified as "
                    f"{pred_disease} ({prediction_result.get('predicted_class', '')}). "
                    f"Please upload a valid {disease_label} microscopic smear image in this section."
                )
            )

        inferred_items.append({
            "slot_key": slot_key,
            "disease_label": disease_label,
            "file_path": file_path,
            "local_heatmap": local_heatmap,
            "prediction_result": prediction_result,
        })

    # Phase 2: Instant Database Persistence with local URLs
    db_predictions = []
    for item in inferred_items:
        pred_res = item["prediction_result"]
        local_in_url = f"/static/uploads/{item['file_path'].name}"
        local_hm_url = f"/static/heatmaps/{item['local_heatmap'].name}" if item["local_heatmap"] else None

        pred_res["heatmap_url"] = local_hm_url
        pred_res["test_label"]  = item["disease_label"]

        db_pred = Prediction(
            user_id           = user_id,
            input_image_path  = local_in_url,
            heatmap_path      = local_hm_url,
            report_path       = None,
            predicted_disease = pred_res["predicted_disease"],
            predicted_class   = pred_res["predicted_class"],
            confidence        = pred_res["confidence"],
            certainty         = pred_res["certainty"],
            risk_level        = pred_res["risk_level"],
            patient_name      = patient_name,
            phone_number      = phone_number,
            notes             = (
                f"[Comprehensive Panel | {item['disease_label']}] "
                f"Patient: {patient_name} | Phone: {phone_number or 'N/A'}"
            ),
        )
        db.add(db_pred)
        db_predictions.append((db_pred, pred_res, item))

    # Single commit for all comprehensive predictions
    db.commit()

    sync_payload = []
    for db_pred, pred_res, item in db_predictions:
        db.refresh(db_pred)
        prediction_ids.append(db_pred.id)
        pred_res["prediction_id"] = db_pred.id
        pred_res["created_at"]    = db_pred.created_at.isoformat() if db_pred.created_at else None
        findings.append(pred_res)
        sync_payload.append({
            "pred_id": db_pred.id,
            "file_path": str(item["file_path"]),
            "local_heatmap": str(item["local_heatmap"]) if item["local_heatmap"] and item["local_heatmap"].exists() else None
        })

    # Set canonical combined report route on first prediction
    if prediction_ids:
        first_pred = db.query(Prediction).filter(Prediction.id == prediction_ids[0]).first()
        if first_pred:
            first_pred.report_path = f"/predict/combined-report/{prediction_ids[0]}"
            db.commit()

    # Phase 3: Background Cloudinary Backup (Non-blocking: user does NOT wait for this!)
    background_tasks.add_task(background_sync_batch, sync_payload)

    import gc as _gc
    _gc.collect()

    return {
        "patient_name":   patient_name,
        "phone_number":   phone_number or "N/A",
        "tests_run":      len(findings),
        "findings":       findings,
        "prediction_ids": prediction_ids,
        "report_url":     f"/predict/combined-report/{prediction_ids[0]}" if prediction_ids else None,
    }


@router.get("/combined-report/{primary_prediction_id}")
def download_combined_report(
    primary_prediction_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Re-generate and serve the combined PDF for a Comprehensive Blood Panel session.
    Finds all DB rows that share the same (patient_name, phone_number, date session)
    flagged as Comprehensive Panel notes.
    """
    primary = db.query(Prediction).filter(Prediction.id == primary_prediction_id).first()
    if not primary:
        raise HTTPException(status_code=404, detail="Report not found")

    patient_name  = primary.patient_name or "User"
    phone_number  = primary.phone_number  or "N/A"

    # Collect all sub-predictions that belong to this comprehensive session.
    # They share the same patient_name + phone_number and have the
    # "[Comprehensive Panel" marker in notes.  Limit to a small time window
    # (60 seconds) to avoid mixing unrelated historical records.
    from datetime import timedelta
    session_start = primary.created_at
    session_end   = session_start + timedelta(seconds=90)

    siblings = (
        db.query(Prediction)
        .filter(
            Prediction.patient_name  == primary.patient_name,
            Prediction.phone_number  == primary.phone_number,
            Prediction.notes.like("%[Comprehensive Panel%"),
            Prediction.created_at   >= session_start,
            Prediction.created_at   <= session_end,
        )
        .order_by(Prediction.id.asc())
        .all()
    )

    if not siblings:
        siblings = [primary]

    # Reconstruct findings list
    findings = []
    for pred in siblings:
        r = reconstruct_prediction_result(pred)
        # Extract clean test_label from notes or fallback to predicted_disease
        test_label = pred.predicted_disease or "Blood Test"
        if pred.notes:
            if "[Comprehensive Panel | " in pred.notes:
                try:
                    test_label = pred.notes.split("[Comprehensive Panel | ")[1].split("]")[0].strip()
                except Exception:
                    test_label = pred.predicted_disease or "Blood Test"
            elif " | " in pred.notes and "]" in pred.notes:
                try:
                    test_label = pred.notes.split(" | ")[1].split("]")[0].strip()
                except Exception:
                    test_label = pred.predicted_disease or "Blood Test"

        r["test_label"] = test_label
        findings.append(r)

    combined_pdf_path = generate_combined_report(
        findings     = findings,
        patient_name = patient_name,
        phone_number = phone_number,
    )

    background_tasks.add_task(delete_temp_file, combined_pdf_path)

    headers = {
        "Content-Disposition": f'inline; filename="combined_report_{primary_prediction_id}.pdf"'
    }
    return FileResponse(
        path       = combined_pdf_path,
        media_type = "application/pdf",
        headers    = headers,
    )


@router.get("/history")
def get_prediction_history(
    user_id: Optional[int] = None, 
    phone_number: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get prediction history, optionally filtered by user_id or phone_number, with pagination"""
    query = db.query(Prediction)
    if user_id:
        query = query.filter(Prediction.user_id == user_id)
    if phone_number:
        clean_phone = phone_number.strip()
        query = query.filter(
            (Prediction.phone_number == clean_phone) | 
            (Prediction.notes.contains(clean_phone))
        )
    predictions = query.order_by(Prediction.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for pred in predictions:
        p_name = pred.patient_name
        if not p_name and pred.notes and "Patient: " in pred.notes:
            p_name = pred.notes.split("Patient: ")[1].split(" |")[0]
            
        p_phone = pred.phone_number
        if not p_phone and pred.notes and "Phone: " in pred.notes:
            p_phone = pred.notes.split("Phone: ")[1]

        result.append({
            "id": pred.id,
            "user_id": pred.user_id,
            "patient_name": p_name or "User",
            "phone_number": p_phone or "N/A",
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
    
    p_name = pred.patient_name
    if not p_name and pred.notes and "Patient: " in pred.notes:
        p_name = pred.notes.split("Patient: ")[1].split(" |")[0]
        
    p_phone = pred.phone_number
    if not p_phone and pred.notes and "Phone: " in pred.notes:
        p_phone = pred.notes.split("Phone: ")[1]

    return {
        "id": pred.id,
        "user_id": pred.user_id,
        "patient_name": p_name or "User",
        "phone_number": p_phone or "N/A",
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

@router.get("/patient/{phone_number}")
def get_patient_history_by_phone(phone_number: str, db: Session = Depends(get_db)):
    """Get all past prediction records for a specific patient phone number"""
    clean_phone = phone_number.strip()
    predictions = db.query(Prediction).filter(
        (Prediction.phone_number == clean_phone) | 
        (Prediction.notes.contains(clean_phone))
    ).order_by(Prediction.created_at.desc()).all()

    result = []
    for pred in predictions:
        p_name = pred.patient_name or "User"
        if not pred.patient_name and pred.notes and "Patient: " in pred.notes:
            p_name = pred.notes.split("Patient: ")[1].split(" |")[0]

        result.append({
            "id": pred.id,
            "patient_name": p_name,
            "phone_number": clean_phone,
            "predicted_disease": pred.predicted_disease,
            "predicted_class": pred.predicted_class,
            "confidence": pred.confidence,
            "risk_level": pred.risk_level,
            "created_at": pred.created_at.isoformat() if pred.created_at else None,
            "report_url": format_db_url(pred.report_path, "/static/reports/"),
            "heatmap_url": format_db_url(pred.heatmap_path, "/static/heatmaps/"),
        })
    return result

def clinical_suggestion(predicted_class: str, risk_level: str) -> str:
    if risk_level == "Low Risk":
        return "Model suggests a low-risk finding. Clinical confirmation is still recommended."
    if risk_level == "High Risk":
        return "Please consult a qualified healthcare professional as soon as possible."
    return "Please review this result with a healthcare professional for confirmation."

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
        "suggestion": clinical_suggestion(prediction.predicted_class, prediction.risk_level),
        "heatmap_path": prediction.heatmap_path,
        "heatmap_url": prediction.heatmap_path,
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
        
    patient_name = pred.patient_name
    if not patient_name and pred.notes and "Patient: " in pred.notes:
        patient_name = pred.notes.split("Patient: ")[1].split(" |")[0]
    if not patient_name:
        patient_name = "User"

    phone_number = pred.phone_number
    if not phone_number and pred.notes and "Phone: " in pred.notes:
        phone_number = pred.notes.split("Phone: ")[1]
    if not phone_number:
        phone_number = "N/A"
        
    reconstructed = reconstruct_prediction_result(pred)
    
    # Generate the PDF file dynamically
    report_path = generate_text_report(reconstructed, patient_name=patient_name, phone_number=phone_number)
    
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
