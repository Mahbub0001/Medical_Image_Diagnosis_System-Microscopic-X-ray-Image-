from pathlib import Path
from datetime import datetime
from ..core.config import settings

def generate_text_report(prediction: dict, patient_name: str = "User") -> str:
    report_dir = Path(settings.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"

    content = f"""BloodDetect AI Report
Patient: {patient_name}
Generated: {datetime.utcnow().isoformat()} UTC

Predicted Disease: {prediction['predicted_disease']}
Predicted Class: {prediction['predicted_class']}
Confidence: {prediction['confidence']:.4f}
Certainty: {prediction['certainty']}
Risk Level: {prediction['risk_level']}

Suggestion:
{prediction['suggestion']}

Probabilities:
{prediction['probabilities']}
"""

    report_path.write_text(content, encoding="utf-8")
    return str(report_path)
