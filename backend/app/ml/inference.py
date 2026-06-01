from pathlib import Path
from typing import Dict
import uuid
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt

from ..core.config import settings
from .model_loader import RegistryModelLoader

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def certainty_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "High"
    if confidence >= 0.60:
        return "Medium"
    return "Low"

def risk_level_from_prediction(predicted_class: str, confidence: float) -> str:
    if predicted_class.lower() in {"healthy", "normal", "uninfected", "benign"}:
        return "Low Risk"
    if confidence >= 0.90:
        return "High Risk"
    if confidence >= 0.70:
        return "Moderate Risk"
    return "Review Needed"

def clinical_suggestion(predicted_class: str, risk_level: str) -> str:
    if risk_level == "Low Risk":
        return "Model suggests a low-risk finding. Clinical confirmation is still recommended."
    if risk_level == "High Risk":
        return "Please consult a qualified healthcare professional as soon as possible."
    return "Please review this result with a healthcare professional for confirmation."

def save_placeholder_heatmap(image_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    arr = np.array(image)
    plt.figure(figsize=(5, 5))
    plt.imshow(arr)
    plt.axis("off")
    out_path = Path(settings.heatmap_dir) / f"{uuid.uuid4().hex}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", pad_inches=0)
    plt.close()
    return str(out_path)

def run_ensemble(image_path: str, disease_key: str) -> Dict:
    loader = RegistryModelLoader(settings.model_registry_path)
    registry = loader.load_registry()
    disease_entry = registry[disease_key]

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)

    weighted_probs = None
    class_names = None

    for model_key, info in disease_entry["models"].items():
        model, current_class_names, meta = loader.load_model(disease_key, model_key)
        probs = torch.softmax(model(tensor), dim=1).detach().cpu().numpy()[0]
        weight = info["weight"]
        if weighted_probs is None:
            weighted_probs = probs * weight
        else:
            weighted_probs += probs * weight
        class_names = current_class_names

    pred_idx = int(np.argmax(weighted_probs))
    confidence = float(weighted_probs[pred_idx])
    predicted_class = class_names[pred_idx]

    heatmap_path = save_placeholder_heatmap(image_path)

    return {
        "predicted_disease": disease_entry["display_name"],
        "predicted_class": predicted_class,
        "confidence": confidence,
        "certainty": certainty_label(confidence),
        "risk_level": risk_level_from_prediction(predicted_class, confidence),
        "probabilities": {class_names[i]: float(weighted_probs[i]) for i in range(len(class_names))},
        "suggestion": clinical_suggestion(predicted_class, risk_level_from_prediction(predicted_class, confidence)),
        "heatmap_url": f"/static/heatmaps/{Path(heatmap_path).name}",
        "report_url": None,
    }
