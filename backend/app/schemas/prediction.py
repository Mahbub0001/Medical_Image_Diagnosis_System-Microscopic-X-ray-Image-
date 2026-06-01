from pydantic import BaseModel
from typing import Dict, Optional

class PredictionResponse(BaseModel):
    predicted_disease: str
    predicted_class: str
    confidence: float
    certainty: str
    risk_level: str
    probabilities: Dict[str, float]
    suggestion: str
    heatmap_url: Optional[str] = None
    report_url: Optional[str] = None
