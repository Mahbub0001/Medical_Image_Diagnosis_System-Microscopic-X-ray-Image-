# Hugging Face Migration — Agent Prompt

## Project Overview

A FastAPI backend (Render, 512MB RAM) for medical image classification (blood cells, lung X-rays) that OOM crashes because it loads multiple PyTorch models. Goal: offload inference to Hugging Face Space, keep Render only for API gateway + DB + auth.

## Project Structure (backend)

```
backend/
  requirements.txt
  .env
  app/
    main.py              # FastAPI app
    core/config.py       # Settings class
    ml/
      registry.json      # Model registry (5 disease keys)
      model_loader.py    # Loads ResNet18/MobileNet/EfficientNet from .pth
      inference.py       # run_ensemble() + run_yolo_prediction() + Grad-CAM
      routers.py         # RoutingCNN, RoutingNet for image domain check
    api/routes/
      prediction.py      # /predict/analyze endpoint
    services/
      cloudinary_service.py
      image_validation.py
      report_service.py
    db/
      models.py          # User, Prediction ORM
      session.py
```

## Models to Migrate

| File | Model Type | Disease |
|------|-----------|---------|
| `resnet18_router_best.pth` | ResNet18 (4-class router) | Router |
| `resnet18_malaria.pth` | ResNet18 (2-class) | Malaria |
| `resnet18_leukemia_corrected.pth` | ResNet18 (4-class) | Leukemia |
| `resnet18_anemia.pth` | ResNet18 (2-class) | Anemia |
| `resnet18_lung.pth` | ResNet18 (3-class) | Lung |
| `routing_best_blood.pth` | RoutingCNN (2-class) | Blood router |
| `routing_best_lungs.pth` | RoutingNet (2-class) | Lung router |
| `blood_combined_yolo_11s.pt` | YOLOv11 (8-class) | Blood cells |

## Step-by-Step Task

### Step 1: Upload weights to Hugging Face Hub

Create a HF model repository named `<your-username>/blooddetect-models` (private recommended).

Upload all .pth/.pt files using `huggingface_hub` Python SDK:
```python
from huggingface_hub import HfApi
api = HfApi()
api.upload_file(
    path_or_fileobj="resnet18_malaria.pth",
    path_in_repo="resnet18_malaria.pth",
    repo_id="<your-username>/blooddetect-models",
    repo_type="model"
)
```

### Step 2: Create Hugging Face Space

Create a Gradio Space at `https://huggingface.co/spaces/<your-username>/blooddetect-inference` with:
- **SDK**: Gradio (NO Dockerfile needed)
- **Hardware**: CPU (16GB RAM free) — upgrade to GPU later if needed
- **Visibility**: Private (or public, up to user)

#### app.py for the Space

```python
import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import json
import gradio as gr
from huggingface_hub import hf_hub_download

# --- Download & Cache Models from HF Hub ---
REPO_ID = "<your-username>/blooddetect-models"

MODEL_CONFIGS = {
    "malaria": {
        "weights": "resnet18_malaria.pth",
        "class_names": ["Parasitized", "Uninfected"],
        "builder": "resnet18"
    },
    "leukemia": {
        "weights": "resnet18_leukemia_corrected.pth",
        "class_names": ["Benign", "Early", "Pre", "Pro"],
        "builder": "resnet18"
    },
    "anemia": {
        "weights": "resnet18_anemia.pth",
        "class_names": ["Anemic", "Normal"],
        "builder": "resnet18"
    },
    "lung": {
        "weights": "resnet18_lung.pth",
        "class_names": ["Normal", "Pneumonia", "Tuberculosis"],
        "builder": "resnet18"
    }
}

# Cache loaded models
_model_cache = {}

def build_resnet18(num_classes):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model

BUILDERS = {"resnet18": build_resnet18}

def load_model(disease_key):
    if disease_key in _model_cache:
        return _model_cache[disease_key]
    
    cfg = MODEL_CONFIGS[disease_key]
    # Download from HF Hub (auto-cached on disk)
    weights_path = hf_hub_download(repo_id=REPO_ID, filename=cfg["weights"])
    
    model = BUILDERS[cfg["builder"]](len(cfg["class_names"]))
    state = torch.load(weights_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    for p in model.parameters():
        p.requires_grad = False
    _model_cache[disease_key] = (model, cfg["class_names"])
    return _model_cache[disease_key]

# Image transform
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def predict(image, disease_key):
    model, class_names = load_model(disease_key)
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1).cpu().numpy()[0]
    pred_idx = int(np.argmax(probs))
    return {
        "predicted_class": class_names[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {class_names[i]: float(probs[i]) for i in range(len(class_names))}
    }

# Gradio Interface
with gr.Blocks(title="BloodDetect Inference") as demo:
    gr.Markdown("# BloodDetect AI - Inference API")
    with gr.Row():
        image_input = gr.Image(type="pil", label="Upload Image")
        disease_dropdown = gr.Dropdown(
            choices=list(MODEL_CONFIGS.keys()),
            value="malaria",
            label="Disease Type"
        )
    predict_btn = gr.Button("Predict")
    output_json = gr.JSON(label="Prediction Result")
    predict_btn.click(fn=predict, inputs=[image_input, disease_dropdown], outputs=output_json)

# Enable queuing and API access
demo.queue()
demo.launch()
```

### Step 3: Modify Render Backend

#### 3a. Update requirements.txt

Remove heavy dependencies, add `requests`:
```
fastapi
uvicorn[standard]
python-multipart
pydantic
pydantic-settings
sqlalchemy
passlib[bcrypt]
python-jose[cryptography]
Pillow
numpy
matplotlib
psycopg2-binary
cloudinary
email-validator
reportlab
requests
```

#### 3b. Add HF Space URL to config.py

```python
class Settings(BaseSettings):
    # ... existing fields ...
    hf_space_url: str = ""  # e.g., "https://<your-username>-blooddetect-inference.hf.space"
```

Add to .env:
```
HF_SPACE_URL=https://<your-username>-blooddetect-inference.hf.space
```

#### 3c. Create new service: backend/app/services/hf_inference.py

```python
import requests
import base64
from pathlib import Path
from ..core.config import settings

HF_API = f"{settings.hf_space_url}/api/predict"

def predict_with_hf(image_path: str, disease_key: str) -> dict:
    """Send image to HF Space for inference."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Gradio API expects base64 or file upload
    response = requests.post(
        HF_API,
        json={
            "data": [
                {"path": image_path, "data": base64.b64encode(image_bytes).decode()},
                disease_key
            ]
        },
        timeout=60
    )
    response.raise_for_status()
    result = response.json()
    return result["data"][0]  # Gradio returns list of outputs
```

#### 3d. Modify inference.py

Replace the model-loading code in `run_ensemble()` and `run_yolo_prediction()` with calls to `predict_with_hf()`. The Grad-CAM heatmap can either:
- Be generated on the HF Space side (and returned as image bytes), OR
- Be replaced with simpler visualization on Render (no PyTorch needed)
- Simplest: return empty/canned heatmap and note "Grad-CAM unavailable in serverless mode"

#### 3e. Modify prediction.py

Remove unused imports of local model loader/routers:
- Remove: `from ...ml.inference import run_ensemble, ...`
- Remove: `from ...ml.routers import run_image_routing_check, ...`
- Remove: `from ...ml.model_loader import clear_model_cache`
- Add: `from ...services.hf_inference import predict_with_hf`
- Replace `run_ensemble()` call with `predict_with_hf()`
- Replace `clear_*_cache()` calls with no-ops or remove

#### 3f. Update routers.py

If routing check is needed on Render side: keep the router code BUT the router weights are very small models (<5MB). These can stay on Render. OR move them to HF Space too.

## Test Flow

1. Deploy HF Space → wait for "Running on https://..."
2. Set `HF_SPACE_URL` in Render .env
3. Deploy Render → hit `/predict/analyze` with image → verify response from HF Space
4. Check Render logs: no PyTorch loading, no OOM

## Notes

- HF Space sleeps after 48hrs inactivity. First request after sleep takes 10-15s (cold start). Can be mitigated with a cron-job ping service or upgrading to HF Space "Upgraded" tier (no sleep).
- Gradio API format: `{"data": [input1, input2, ...]}` returns `{"data": [output1, output2, ...]}`
- For YOLOv11: upload `blood_combined_yolo_11s.pt` to HF Hub too, import YOLO in Space's app.py
- For routing check: either move to HF Space OR keep on Render (small models, low RAM impact)

## Files to Create

- `backend/app/services/hf_inference.py`
- HF Space: `app.py` + `requirements.txt`

## Files to Modify

- `backend/requirements.txt` — remove torch/torchvision/ultralytics, add requests
- `backend/app/core/config.py` — add hf_space_url
- `backend/.env` — add HF_SPACE_URL
- `backend/app/ml/inference.py` — replace with HF calls
- `backend/app/api/routes/prediction.py` — update imports
