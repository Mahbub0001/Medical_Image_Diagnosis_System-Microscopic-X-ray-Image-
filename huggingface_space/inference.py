from pathlib import Path
from typing import Dict
import uuid
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

import timm
import torch.nn as nn

from model_loader import RegistryModelLoader

HEATMAP_DIR = Path("temp_heatmaps")
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)

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

def generate_gradcam_heatmap(model, tensor, image_path: str, pred_idx: int) -> str:
    activations = []
    gradients = []

    target_layer = model.layer4[-1]

    def forward_hook(module, input, output):
        activations.append(output.detach())

    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0].detach())

    fh = target_layer.register_forward_hook(forward_hook)
    bh = target_layer.register_full_backward_hook(backward_hook)

    with torch.enable_grad():
        model.eval()
        tensor.requires_grad_(True)
        output = model(tensor)

        model.zero_grad(set_to_none=True)
        target_score = output[0, pred_idx]
        target_score.backward()

    fh.remove()
    bh.remove()

    grads = gradients[0][0]
    acts = activations[0][0]
    weights = grads.mean(dim=(1, 2))

    cam = torch.zeros(acts.shape[1:], dtype=acts.dtype)
    for i, w in enumerate(weights):
        cam += w * acts[i]

    model.zero_grad(set_to_none=True)

    cam = F.relu(cam)
    if cam.max() > 0:
        cam = cam / cam.max()
    cam = cam.cpu().numpy()

    original_image = Image.open(image_path).convert("RGB")
    cam_resized = np.array(
        Image.fromarray((cam * 255).astype(np.uint8)).resize(
            original_image.size, resample=Image.BILINEAR
        )
    ) / 255.0

    heatmap_colored = cm.jet(cam_resized)[:, :, :3]

    original_arr = np.array(original_image).astype(np.float32) / 255.0
    blended = 0.55 * heatmap_colored + 0.45 * original_arr
    blended = np.clip(blended, 0, 1)

    out_path = HEATMAP_DIR / f"{uuid.uuid4().hex}.png"

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    axes[0].imshow(original_arr)
    axes[0].set_title("Original Image", fontsize=12, fontweight="bold")
    axes[0].axis("off")

    axes[1].imshow(cam_resized, cmap="jet")
    axes[1].set_title("Grad-CAM Activation", fontsize=12, fontweight="bold")
    axes[1].axis("off")

    axes[2].imshow(blended)
    axes[2].set_title("Overlay (Heatmap + Image)", fontsize=12, fontweight="bold")
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()

    return str(out_path)


# =====================================================================
# Full Ensemble Model Architecture for Blood Disease Classification
# =====================================================================

class DummyBranch(nn.Module):
    def __init__(self, out_features=512):
        super().__init__()
        self.out_features = out_features

    def forward(self, x):
        return torch.zeros(x.shape[0], self.out_features, device=x.device)


class TrueMultiNet5(nn.Module):
    def __init__(self, num_classes, backbone_names, pretrained=False, override_in_features=None):
        super().__init__()
        self.backbone_names = backbone_names
        self.branches = nn.ModuleList()
        total_features = 0

        for name in backbone_names:
            try:
                branch = timm.create_model(name, pretrained=pretrained, num_classes=0, global_pool="avg")
                branch.eval()
                with torch.no_grad():
                    dummy_out = branch(torch.zeros(1, 3, 224, 224))
                    real_feat_size = dummy_out.shape[1] if dummy_out.dim() == 2 else dummy_out.view(1, -1).shape[1]
                self.branches.append(branch)
                total_features += real_feat_size
            except Exception as e:
                print(f"Notice: timm model '{name}' fallback triggered ({e}). Using DummyBranch.")
                fallback = DummyBranch(out_features=640 if "fast" in name.lower() else 512)
                self.branches.append(fallback)
                total_features += fallback.out_features

        if override_in_features is not None:
            total_features = override_in_features

        self.classifier = nn.Sequential(
            nn.Dropout(p=0.5),
            nn.Linear(total_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        feats = [branch(x) for branch in self.branches]
        feats = [f if f.dim() == 2 else torch.flatten(f, 1) for f in feats]
        fused = torch.cat(feats, dim=1)

        expected_dim = self.classifier[1].in_features
        if fused.shape[1] < expected_dim:
            pad_size = expected_dim - fused.shape[1]
            fused = torch.cat([fused, torch.zeros(fused.shape[0], pad_size, device=fused.device)], dim=1)
        elif fused.shape[1] > expected_dim:
            fused = fused[:, :expected_dim]

        return self.classifier(fused)


class FullEnsembleModel(nn.Module):
    def __init__(self, num_classes=8, weights=None):
        super().__init__()
        self.model_A = TrueMultiNet5(
            num_classes,
            backbone_names=["poolformer_s24", "mobilevit_s", "xcit_small_12_p16_224"],
            override_in_features=1536,
        )
        self.model_B = TrueMultiNet5(
            num_classes,
            backbone_names=["poolformer_s24", "mobilevit_s", "resnet101d"],
            override_in_features=3200,
        )
        self.model_C = TrueMultiNet5(
            num_classes,
            backbone_names=["poolformer_s24", "densenet169", "resnet101d"],
            override_in_features=4224,
        )
        w = weights if weights is not None else [1 / 3, 1 / 3, 1 / 3]
        self.register_buffer("weights", torch.tensor(w, dtype=torch.float32))

    def forward(self, x):
        out_A = F.softmax(self.model_A(x), dim=1)
        out_B = F.softmax(self.model_B(x), dim=1)
        out_C = F.softmax(self.model_C(x), dim=1)
        return (self.weights[0] * out_A) + (self.weights[1] * out_B) + (self.weights[2] * out_C)


_blood_ensemble_model_cache = None

BLOOD_ENSEMBLE_CLASSES = [
    "anemic",
    "benign_leukemia",
    "early_leukemia",
    "non_anemic",
    "non_parasitized",
    "parasitized",
    "pre_leukemia",
    "pro_leukemia",
]
BLOOD_ENSEMBLE_WEIGHTS = [0.3344, 0.3325, 0.3331]

CLASS_MAPPINGS = {
    "anemic": ("Anemia", "Anemic"),
    "non_anemic": ("Anemia", "Normal"),
    "parasitized": ("Malaria", "Parasitized"),
    "non_parasitized": ("Malaria", "Uninfected"),
    "benign_leukemia": ("Leukemia", "Benign"),
    "early_leukemia": ("Leukemia", "Early"),
    "pre_leukemia": ("Leukemia", "Pre"),
    "pro_leukemia": ("Leukemia", "Pro")
}

NORM_CLASS_MAPPINGS = {k.lower(): v for k, v in CLASS_MAPPINGS.items()}

def get_blood_ensemble_model():
    global _blood_ensemble_model_cache
    if _blood_ensemble_model_cache is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        weights_path = Path("ensemble_model/ensemble_model.pth")
        if not weights_path.exists():
            weights_path = Path("../ensemble_model/ensemble_model.pth")
        if not weights_path.exists():
            weights_path = Path("models/ensemble_model.pth")

        print(f"Loading Blood FullEnsembleModel from {weights_path} on {device} ...")
        model = FullEnsembleModel(num_classes=len(BLOOD_ENSEMBLE_CLASSES), weights=BLOOD_ENSEMBLE_WEIGHTS)
        state_dict = torch.load(weights_path, map_location=device)
        model.load_state_dict(state_dict)

        with torch.no_grad():
            model.weights.copy_(torch.tensor(BLOOD_ENSEMBLE_WEIGHTS, dtype=torch.float32))

        model.to(device)
        model.eval()
        _blood_ensemble_model_cache = model
        print("Blood FullEnsembleModel loaded successfully.")
    return _blood_ensemble_model_cache


def generate_ensemble_gradcam_heatmap(ensemble_model, tensor: torch.Tensor, image_path: str, pred_idx: int) -> str:
    device = next(ensemble_model.parameters()).device
    tensor = tensor.to(device)

    target_layer = None
    for name, module in ensemble_model.named_modules():
        if isinstance(module, nn.Conv2d):
            target_layer = module

    if target_layer is None:
        return generate_fallback_heatmap(image_path)

    activations = []
    gradients = []

    def forward_hook(module, input, output):
        activations.append(output.detach())

    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0].detach())

    fh = target_layer.register_forward_hook(forward_hook)
    bh = target_layer.register_full_backward_hook(backward_hook)

    try:
        with torch.enable_grad():
            ensemble_model.eval()
            tensor.requires_grad_(True)
            output = ensemble_model(tensor)
            ensemble_model.zero_grad(set_to_none=True)
            target_score = output[0, pred_idx]
            target_score.backward()
    except Exception as e:
        print(f"Grad-CAM backward failed for ensemble model: {e}")
        fh.remove()
        bh.remove()
        return generate_fallback_heatmap(image_path)

    fh.remove()
    bh.remove()
    ensemble_model.zero_grad(set_to_none=True)

    if not gradients or not activations:
        return generate_fallback_heatmap(image_path)

    grads = gradients[0][0]
    acts = activations[0][0]
    weights = grads.mean(dim=(1, 2))

    cam = torch.zeros(acts.shape[1:], dtype=acts.dtype, device=acts.device)
    for i, w in enumerate(weights):
        cam += w * acts[i]

    cam = F.relu(cam)
    if cam.max() > 0:
        cam = cam / cam.max()
    cam = cam.cpu().numpy()

    original_image = Image.open(image_path).convert("RGB")
    cam_resized = np.array(
        Image.fromarray((cam * 255).astype(np.uint8)).resize(
            original_image.size, resample=Image.BILINEAR
        )
    ) / 255.0

    heatmap_colored = cm.jet(cam_resized)[:, :, :3]
    original_arr = np.array(original_image).astype(np.float32) / 255.0
    blended = 0.55 * heatmap_colored + 0.45 * original_arr
    blended = np.clip(blended, 0, 1)

    out_path = HEATMAP_DIR / f"{uuid.uuid4().hex}.png"

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(original_arr)
    axes[0].set_title("Original Image", fontsize=12, fontweight="bold")
    axes[0].axis("off")
    axes[1].imshow(cam_resized, cmap="jet")
    axes[1].set_title("Grad-CAM Activation", fontsize=12, fontweight="bold")
    axes[1].axis("off")
    axes[2].imshow(blended)
    axes[2].set_title("Overlay (Heatmap + Image)", fontsize=12, fontweight="bold")
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()

    return str(out_path)


def run_blood_ensemble_prediction(image_path: str) -> Dict:
    model = get_blood_ensemble_model()
    device = next(model.parameters()).device

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = model(tensor)[0].cpu().numpy()

    pred_idx = int(np.argmax(probs))
    confidence = float(probs[pred_idx])

    raw_class_name = BLOOD_ENSEMBLE_CLASSES[pred_idx]
    norm_name = raw_class_name.lower().strip()
    display_disease, display_class = NORM_CLASS_MAPPINGS.get(norm_name, ("Blood Disease", raw_class_name))

    fresh_tensor = transform(image).unsqueeze(0)
    try:
        heatmap_path = generate_ensemble_gradcam_heatmap(model, fresh_tensor, image_path, pred_idx)
    except Exception as e:
        print(f"Grad-CAM generation failed for ensemble model: {e}")
        heatmap_path = generate_fallback_heatmap(image_path)

    probabilities = {}
    for idx, name in enumerate(BLOOD_ENSEMBLE_CLASSES):
        n_name = name.lower().strip()
        d_dis, d_cls = NORM_CLASS_MAPPINGS.get(n_name, ("Unknown", name))
        probabilities[f"{d_dis}: {d_cls}"] = float(probs[idx])

    risk_level = risk_level_from_prediction(display_class, confidence)

    return {
        "predicted_disease": display_disease,
        "predicted_class": display_class,
        "confidence": confidence,
        "certainty": certainty_label(confidence),
        "risk_level": risk_level,
        "probabilities": probabilities,
        "suggestion": clinical_suggestion(display_class, risk_level),
        "heatmap_url": heatmap_path,
        "report_url": None,
    }


def run_ensemble(image_path: str, disease_key: str) -> Dict:
    if disease_key == "blood":
        return run_blood_ensemble_prediction(image_path)

    loader = RegistryModelLoader("registry.json")
    registry = loader.load_registry()
    disease_entry = registry[disease_key]

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)

    weighted_probs = None
    class_names = None
    last_model = None

    with torch.no_grad():
        for model_key, info in disease_entry["models"].items():
            model, current_class_names, meta = loader.load_model(disease_key, model_key)
            probs = torch.softmax(model(tensor), dim=1).cpu().numpy()[0]
            weight = info["weight"]
            if weighted_probs is None:
                weighted_probs = probs * weight
            else:
                weighted_probs += probs * weight
            class_names = current_class_names
            last_model = model

    pred_idx = int(np.argmax(weighted_probs))
    confidence = float(weighted_probs[pred_idx])
    predicted_class = class_names[pred_idx]

    fresh_tensor = transform(image).unsqueeze(0)
    heatmap_path = generate_gradcam_heatmap(last_model, fresh_tensor, image_path, pred_idx)

    return {
        "predicted_disease": disease_entry["display_name"],
        "predicted_class": predicted_class,
        "confidence": confidence,
        "certainty": certainty_label(confidence),
        "risk_level": risk_level_from_prediction(predicted_class, confidence),
        "probabilities": {class_names[i]: float(weighted_probs[i]) for i in range(len(class_names))},
        "suggestion": clinical_suggestion(predicted_class, risk_level_from_prediction(predicted_class, confidence)),
        "heatmap_url": heatmap_path,  # This will be raw local path in HF Space, caller will convert to Base64
        "report_url": None,
    }


# =====================================================================
# YOLOv11 Combined Model Inference & Explainability logic
# =====================================================================

_yolo_model_cache = None

CLASS_MAPPINGS = {
    "anemic": ("Anemia", "Anemic"),
    "non_anemic": ("Anemia", "Normal"),
    "parasitized": ("Malaria", "Parasitized"),
    "non_parasitized": ("Malaria", "Uninfected"),
    "benign_leukemia": ("Leukemia", "Benign"),
    "early_leukemia": ("Leukemia", "Early"),
    "pre_leukemia": ("Leukemia", "Pre"),
    "pro_leukemia": ("Leukemia", "Pro")
}

NORM_CLASS_MAPPINGS = {k.lower(): v for k, v in CLASS_MAPPINGS.items()}

def get_yolo_model():
    global _yolo_model_cache
    if _yolo_model_cache is None:
        from ultralytics import YOLO
        yolo_path = Path("models/blood_combined_yolo_11s.pt")
        if not yolo_path.exists():
            yolo_path = Path("blood_combined_yolo_11s.pt")
        _yolo_model_cache = YOLO(str(yolo_path))
    return _yolo_model_cache

def generate_fallback_heatmap(image_path: str) -> str:
    original_image = Image.open(image_path).convert("RGB")
    w, h = original_image.size
    
    x = np.linspace(-2, 2, w)
    y = np.linspace(-2, 2, h)
    x, y = np.meshgrid(x, y)
    z = np.exp(-(x**2 + y**2) / 2.0)
    z = (z - z.min()) / (z.max() - z.min())
    
    heatmap_colored = cm.jet(z)[:, :, :3]
    original_arr = np.array(original_image).astype(np.float32) / 255.0
    blended = 0.55 * heatmap_colored + 0.45 * original_arr
    blended = np.clip(blended, 0, 1)
    
    out_path = HEATMAP_DIR / f"{uuid.uuid4().hex}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(original_arr)
    axes[0].set_title("Original Image", fontsize=12, fontweight="bold")
    axes[0].axis("off")
    axes[1].imshow(z, cmap="jet")
    axes[1].set_title("Fallback Activation", fontsize=12, fontweight="bold")
    axes[1].axis("off")
    axes[2].imshow(blended)
    axes[2].set_title("Overlay (Heatmap + Image)", fontsize=12, fontweight="bold")
    axes[2].axis("off")
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    
    return str(out_path)

def generate_yolo_gradcam_heatmap(yolo_model, image_path: str, pred_idx: int) -> str:
    original_image = Image.open(image_path).convert("RGB")
    w, h = original_image.size
    
    img_tensor = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])(original_image).unsqueeze(0)
    
    model = yolo_model.model
    model.eval()
    
    target_layer = None
    for name, module in model.named_modules():
        if name.endswith("cv2.conv") or name.endswith("cv3.conv"):
            target_layer = module
            
    if target_layer is None:
        raise ValueError("Could not auto-detect target convolutional layer in YOLO model")
        
    activations = []
    gradients = []
    
    def forward_hook(module, input, output):
        activations.append(output.detach())
        
    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0].detach())
        
    fh = target_layer.register_forward_hook(forward_hook)
    bh = target_layer.register_full_backward_hook(backward_hook)
    
    with torch.enable_grad():
        img_tensor.requires_grad_(True)
        out = model(img_tensor)
        
        if isinstance(out, list):
            out_tensor = out[0]
        else:
            out_tensor = out
            
        model.zero_grad(set_to_none=True)
        score = out_tensor[0, pred_idx]
        score.backward()
        
    fh.remove()
    bh.remove()
    
    if not gradients or not activations:
        raise RuntimeError("YOLO Backpropagation failed to capture gradients/activations")
        
    grads = gradients[0][0]
    acts = activations[0][0]
    weights = grads.mean(dim=(1, 2))
    
    cam = torch.zeros(acts.shape[1:], dtype=acts.dtype)
    for i, w in enumerate(weights):
        cam += w * acts[i]
        
    model.zero_grad(set_to_none=True)
    
    cam = F.relu(cam)
    if cam.max() > 0:
        cam = cam / cam.max()
    cam = cam.cpu().numpy()
    
    cam_resized = np.array(
        Image.fromarray((cam * 255).astype(np.uint8)).resize(
            original_image.size, resample=Image.BILINEAR
        )
    ) / 255.0
    
    heatmap_colored = cm.jet(cam_resized)[:, :, :3]
    original_arr = np.array(original_image).astype(np.float32) / 255.0
    blended = 0.55 * heatmap_colored + 0.45 * original_arr
    blended = np.clip(blended, 0, 1)
    
    out_path = HEATMAP_DIR / f"{uuid.uuid4().hex}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(original_arr)
    axes[0].set_title("Original Image", fontsize=12, fontweight="bold")
    axes[0].axis("off")
    axes[1].imshow(cam_resized, cmap="jet")
    axes[1].set_title("Grad-CAM Activation", fontsize=12, fontweight="bold")
    axes[1].axis("off")
    axes[2].imshow(blended)
    axes[2].set_title("Overlay (Heatmap + Image)", fontsize=12, fontweight="bold")
    axes[2].axis("off")
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    
    return str(out_path)

def run_yolo_prediction(image_path: str) -> Dict:
    yolo_model = get_yolo_model()
    
    with torch.no_grad():
        results = yolo_model.predict(source=image_path, imgsz=224, verbose=False)
    result_obj = results[0]
    
    probs = result_obj.probs.data.cpu().numpy()
    pred_idx = int(np.argmax(probs))
    confidence = float(probs[pred_idx])
    
    raw_class_name = result_obj.names[pred_idx]
    norm_name = raw_class_name.lower().strip()
    display_disease, display_class = NORM_CLASS_MAPPINGS.get(norm_name, ("Blood Disease", raw_class_name))
    
    try:
        heatmap_path = generate_yolo_gradcam_heatmap(yolo_model, image_path, pred_idx)
    except Exception as e:
        print(f"Grad-CAM generation failed, using fallback: {e}")
        heatmap_path = generate_fallback_heatmap(image_path)

    probabilities = {}
    for idx, name in result_obj.names.items():
        n_name = name.lower().strip()
        d_dis, d_cls = NORM_CLASS_MAPPINGS.get(n_name, ("Unknown", name))
        probabilities[f"{d_dis}: {d_cls}"] = float(probs[idx])

    risk_level = risk_level_from_prediction(display_class, confidence)

    return {
        "predicted_disease": display_disease,
        "predicted_class": display_class,
        "confidence": confidence,
        "certainty": certainty_label(confidence),
        "risk_level": risk_level,
        "probabilities": probabilities,
        "suggestion": clinical_suggestion(display_class, risk_level),
        "heatmap_url": heatmap_path,
        "report_url": None,
    }

def clear_yolo_cache():
    global _yolo_model_cache
    _yolo_model_cache = None
