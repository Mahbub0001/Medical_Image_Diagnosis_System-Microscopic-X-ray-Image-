import base64
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import re

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Local ML inference and service imports
from routers import run_image_routing_check
from inference import run_ensemble, clinical_suggestion, risk_level_from_prediction
from image_validation import validate_uploaded_image, resize_image_in_place
from report_service import generate_text_report, generate_combined_report

# ── Directory setup ───────────────────────────────────────────────────────────
UPLOAD_DIR = Path("storage/uploads")
REPORT_DIR = Path("storage/reports")
HEATMAP_DIR = Path("storage/heatmaps")
TEMP_DIR = Path("temp_files")

for d in [UPLOAD_DIR, REPORT_DIR, HEATMAP_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Database Setup (SQLite for Space) ──────────────────────────────────────────
DATABASE_URL = "sqlite:///./biolens.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String(120), nullable=True)
    phone_number = Column(String(30), nullable=True, index=True)
    input_image_path = Column(String(255), nullable=False)
    heatmap_path = Column(String(255), nullable=True)
    report_path = Column(String(255), nullable=True)
    predicted_disease = Column(String(100), nullable=False)
    predicted_class = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    certainty = Column(String(20), nullable=False)
    risk_level = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── App & CORS ────────────────────────────────────────────────────────────────
app = FastAPI(title="BioLens Medical AI Cloud Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"(https?://.*|capacitor://.*)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static directories for image & report assets
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static/heatmaps", StaticFiles(directory=str(HEATMAP_DIR)), name="heatmaps")
app.mount("/static/reports", StaticFiles(directory=str(REPORT_DIR)), name="reports")

# ── Health Endpoints ──────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "BioLens API is running"}

@app.get("/health")
def health():
    return {"status": "ok", "message": "BioLens API is healthy"}

# ── Legacy /predict Endpoint ──────────────────────────────────────────────────
@app.post("/predict")
async def predict_legacy(
    disease_key: str = Form(...),
    file: UploadFile = File(...)
):
    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"

    temp_image_path = TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    try:
        with open(temp_image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if disease_key in {"blood", "lung"}:
            is_valid_domain, domain_error = run_image_routing_check(str(temp_image_path), disease_key)
            if not is_valid_domain:
                raise HTTPException(status_code=400, detail={"message": "Invalid domain", "error": domain_error})

        result = run_ensemble(str(temp_image_path), disease_key=disease_key)

        heatmap_path = Path(result["heatmap_url"])
        if heatmap_path.exists():
            with open(heatmap_path, "rb") as image_file:
                result["heatmap_base64"] = base64.b64encode(image_file.read()).decode("utf-8")
        else:
            result["heatmap_base64"] = None

        return result
    finally:
        try:
            temp_image_path.unlink(missing_ok=True)
        except Exception:
            pass

# ── Single Analysis Endpoint (Used by BioLens App & Web) ──────────────────────
@app.post("/predict/analyze")
async def analyze_image(
    disease_key: str = Form("blood"),
    patient_name: str = Form("User"),
    phone_number: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"

    upload_file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    content = await file.read()
    with open(upload_file_path, "wb") as f:
        f.write(content)

    try:
        # 1. Routing check
        if disease_key in {"blood", "lung"}:
            is_valid, domain_err = run_image_routing_check(str(upload_file_path), disease_key)
            if not is_valid:
                raise HTTPException(status_code=400, detail=domain_err)

        # 2. Run ensemble
        result = run_ensemble(str(upload_file_path), disease_key=disease_key)

        # 3. Preserve Grad-CAM heatmap permanently
        orig_heatmap = Path(result["heatmap_url"])
        heatmap_name = f"{uuid.uuid4().hex}.png"
        perm_heatmap_path = HEATMAP_DIR / heatmap_name
        if orig_heatmap.exists():
            shutil.copyfile(orig_heatmap, perm_heatmap_path)
            try:
                orig_heatmap.unlink()
            except Exception:
                pass
        heatmap_rel_url = f"/static/heatmaps/{heatmap_name}"

        # 4. Save to database
        db_pred = Prediction(
            patient_name=patient_name or "User",
            phone_number=phone_number or "",
            input_image_path=f"/static/uploads/{upload_file_path.name}",
            heatmap_path=heatmap_rel_url,
            report_path=f"/predict/report/pending",
            predicted_disease=result["predicted_disease"],
            predicted_class=result["predicted_class"],
            confidence=float(result["confidence"]),
            certainty=result["certainty"],
            risk_level=result["risk_level"],
            notes=f"Patient: {patient_name} | Phone: {phone_number or 'N/A'}",
        )
        db.add(db_pred)
        db.commit()
        db.refresh(db_pred)

        report_rel_url = f"/predict/report/{db_pred.id}"
        db_pred.report_path = report_rel_url
        db.commit()

        return {
            "predicted_disease": result["predicted_disease"],
            "predicted_class": result["predicted_class"],
            "confidence": result["confidence"],
            "certainty": result["certainty"],
            "risk_level": result["risk_level"],
            "probabilities": result["probabilities"],
            "suggestion": result["suggestion"],
            "heatmap_url": heatmap_rel_url,
            "report_url": report_rel_url,
            "prediction_id": db_pred.id,
            "created_at": db_pred.created_at.isoformat() if db_pred.created_at else datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# ── Comprehensive Panel Endpoint ──────────────────────────────────────────────
@app.post("/predict/analyze-comprehensive")
async def analyze_comprehensive(
    patient_name: str = Form("User"),
    phone_number: Optional[str] = Form(None),
    anemia_image: Optional[UploadFile] = File(None),
    malaria_image: Optional[UploadFile] = File(None),
    leukemia_image: Optional[UploadFile] = File(None),
    file_anemia: Optional[UploadFile] = File(None),
    file_malaria: Optional[UploadFile] = File(None),
    file_leukemia: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    phone_clean = phone_number.strip() if phone_number else ""
    if phone_clean and not re.match(r"^01\d{9}$", phone_clean):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number! It must start with '01' and be exactly 11 digits (e.g. 01712345678)."
        )

    tests_input = [
        ("anemia", "Anemia", anemia_image or file_anemia),
        ("malaria", "Malaria", malaria_image or file_malaria),
        ("leukemia", "Leukemia", leukemia_image or file_leukemia),
    ]

    active = [(k, l, f) for k, l, f in tests_input if f is not None]
    if not active:
        raise HTTPException(status_code=400, detail="Please upload at least one blood smear image.")

    findings = []
    saved_files = []
    highest_risk = "Low Risk"
    risk_rank = {"Low Risk": 0, "Review Needed": 1, "Moderate Risk": 2, "High Risk": 3}

    for slot_key, disease_label, uploaded_file in active:
        suffix = Path(uploaded_file.filename or "image.jpg").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            suffix = ".jpg"

        file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
        content = await uploaded_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        saved_files.append(file_path)

        # Image validation
        val_res = validate_uploaded_image(str(file_path))
        if not val_res["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"{disease_label} image: " + ", ".join(val_res["errors"])
            )
        resize_image_in_place(str(file_path), max_size=1024)

        # Domain routing check
        is_valid_domain, domain_err = run_image_routing_check(str(file_path), "blood")
        if not is_valid_domain:
            raise HTTPException(
                status_code=400,
                detail=f"{disease_label} slot: {domain_err}"
            )

        # AI inference using multi-135 model
        res = run_ensemble(str(file_path), disease_key="blood")

        # Strict Disease Slot Matching Validation
        pred_disease = res.get("predicted_disease", "")
        if pred_disease.lower() != slot_key.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Slot Mismatch in '{disease_label}' Section: The uploaded image was identified as "
                    f"{pred_disease} ({res.get('predicted_class', '')}). "
                    f"Please upload a valid {disease_label} microscopic smear image in this section."
                )
            )

        orig_heatmap = Path(res["heatmap_url"])
        heatmap_name = f"{uuid.uuid4().hex}.png"
        perm_heatmap = HEATMAP_DIR / heatmap_name
        if orig_heatmap.exists():
            shutil.copyfile(orig_heatmap, perm_heatmap)
            try:
                orig_heatmap.unlink()
            except Exception:
                pass
        heatmap_rel = f"/static/heatmaps/{heatmap_name}"

        cur_risk = res["risk_level"]
        if risk_rank.get(cur_risk, 0) > risk_rank.get(highest_risk, 0):
            highest_risk = cur_risk

        finding = {
            "test_key": slot_key,
            "test_label": disease_label,
            "predicted_disease": res["predicted_disease"],
            "predicted_class": res["predicted_class"],
            "confidence": res["confidence"],
            "certainty": res["certainty"],
            "risk_level": res["risk_level"],
            "probabilities": res["probabilities"],
            "suggestion": res["suggestion"],
            "heatmap_url": heatmap_rel,
            "local_heatmap_path": str(perm_heatmap),
        }
        findings.append(finding)

        db_row = Prediction(
            patient_name=patient_name or "User",
            phone_number=phone_number or "",
            input_image_path=f"/static/uploads/{file_path.name}",
            heatmap_path=heatmap_rel,
            predicted_disease=res["predicted_disease"],
            predicted_class=res["predicted_class"],
            confidence=float(res["confidence"]),
            certainty=res["certainty"],
            risk_level=res["risk_level"],
            notes=f"Comprehensive Panel: {disease_label} | Patient: {patient_name}",
        )
        db.add(db_row)
        db.commit()

    # Generate real ReportLab combined PDF report
    try:
        combined_pdf_path = generate_combined_report(
            findings=findings,
            patient_name=patient_name or "User",
            phone_number=phone_number or "N/A"
        )
        report_filename = Path(combined_pdf_path).name
        combined_report_url = f"/static/reports/{report_filename}"
    except Exception as e:
        print(f"Failed to generate combined PDF: {e}")
        combined_report_url = None

    if highest_risk == "High Risk":
        recs = [
            "Immediate consultation with a hematologist or specialist is strongly recommended.",
            "Complete blood count (CBC) with peripheral blood smear confirmation advised.",
        ]
    elif highest_risk == "Moderate Risk":
        recs = [
            "Follow-up laboratory testing recommended within 48-72 hours.",
            "Consult primary care physician for clinical correlation.",
        ]
    else:
        recs = [
            "All screened parameters appear within normal limits.",
            "Routine clinical monitoring as advised by your healthcare provider.",
        ]

    return {
        "tests_run": len(findings),
        "findings": findings,
        "composite_risk": highest_risk,
        "recommendations": recs,
        "report_url": combined_report_url,
    }

# ── Report PDF Endpoints ──────────────────────────────────────────────────────
@app.get("/predict/report/{prediction_id}")
def get_prediction_report(prediction_id: int, db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction record not found.")

    finding = {
        "predicted_disease": pred.predicted_disease,
        "predicted_class": pred.predicted_class,
        "confidence": pred.confidence,
        "certainty": pred.certainty,
        "risk_level": pred.risk_level,
        "suggestion": clinical_suggestion(pred.predicted_class, pred.risk_level),
        "heatmap_url": pred.heatmap_path,
        "probabilities": {pred.predicted_class: pred.confidence},
    }

    pdf_path = generate_text_report(
        finding,
        patient_name=pred.patient_name or "User",
        phone_number=pred.phone_number or "N/A"
    )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report_{prediction_id}.pdf"'}
    )

# ── Prediction History ────────────────────────────────────────────────────────
@app.get("/predict/history")
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(limit).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "patient_name": r.patient_name or "User",
            "phone_number": r.phone_number or "N/A",
            "predicted_disease": r.predicted_disease,
            "predicted_class": r.predicted_class,
            "confidence": r.confidence,
            "risk_level": r.risk_level,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "report_url": r.report_path,
            "heatmap_url": r.heatmap_path,
        })
    return out

# ── Admin Dashboard Summary ───────────────────────────────────────────────────
@app.get("/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    total = db.query(Prediction).count()
    disease_counts = db.query(
        Prediction.predicted_disease, 
        func.count(Prediction.id)
    ).group_by(Prediction.predicted_disease).all()
    disease_dict = {disease: count for disease, count in disease_counts}

    normal_cases = db.query(Prediction).filter(
        func.lower(Prediction.predicted_class).in_(['normal', 'uninfected', 'benign', 'healthy'])
    ).count()

    return {
        "total_predictions": total,
        "malaria_cases": disease_dict.get('Malaria', 0),
        "anemia_cases": disease_dict.get('Anemia', 0),
        "leukemia_cases": disease_dict.get('Leukemia', 0),
        "lung_cases": disease_dict.get('Lung X-Ray', 0),
        "abnormal_cases": total - normal_cases,
        "normal_cases": normal_cases
    }
