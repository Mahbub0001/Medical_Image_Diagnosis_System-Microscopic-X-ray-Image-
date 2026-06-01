from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ...db.session import SessionLocal
from ...db.models import Prediction

router = APIRouter(prefix="/admin", tags=["admin"])

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/summary")
def admin_summary(db: Session = Depends(get_db)):
    # Get total predictions
    total_predictions = db.query(Prediction).count()
    
    # Get counts by disease
    disease_counts = db.query(
        Prediction.predicted_disease, 
        func.count(Prediction.id)
    ).group_by(Prediction.predicted_disease).all()
    
    # Build disease counts dictionary
    disease_dict = {disease: count for disease, count in disease_counts}
    
    # Count normal/healthy cases (predicted_class contains 'normal', 'uninfected', or 'benign')
    normal_cases = db.query(Prediction).filter(
        func.lower(Prediction.predicted_class).in_([
            'normal', 'uninfected', 'benign', 'healthy'
        ])
    ).count()
    
    # Calculate average confidence by disease
    confidence_by_disease = db.query(
        Prediction.predicted_disease,
        func.avg(Prediction.confidence)
    ).group_by(Prediction.predicted_disease).all()
    
    accuracy_dict = {disease: round(float(avg_conf), 4) for disease, avg_conf in confidence_by_disease}
    
    return {
        "total_predictions": total_predictions,
        "malaria_cases": disease_dict.get('Malaria', 0),
        "anemia_cases": disease_dict.get('Anemia', 0),
        "leukemia_cases": disease_dict.get('Leukemia', 0),
        "lung_cases": disease_dict.get('Lung X-Ray', 0),
        "normal_cases": normal_cases,
        "disease_breakdown": disease_dict,
        "model_accuracy": accuracy_dict
    }
