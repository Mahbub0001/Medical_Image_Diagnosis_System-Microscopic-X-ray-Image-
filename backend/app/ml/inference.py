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


def generate_gradcam_heatmap(model, tensor, image_path: str, pred_idx: int) -> str:
    """
    Generate a real Grad-CAM heatmap by hooking into ResNet-18's final 
    convolutional layer (layer4), computing gradient-weighted activations, 
    and overlaying the result on the original image.
    """
    # Storage for hooked activations and gradients
    activations = []
    gradients = []

    # Hook the last conv block of ResNet-18
    target_layer = model.layer4[-1]

    def forward_hook(module, input, output):
        activations.append(output.detach())

    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0].detach())

    fh = target_layer.register_forward_hook(forward_hook)
    bh = target_layer.register_full_backward_hook(backward_hook)

    # Forward pass
    model.eval()
    tensor.requires_grad_(True)
    output = model(tensor)

    # Backward pass for the predicted class
    model.zero_grad()
    target_score = output[0, pred_idx]
    target_score.backward()

    # Remove hooks
    fh.remove()
    bh.remove()

    # Compute Grad-CAM weights: global average pool the gradients
    grads = gradients[0][0]        # shape: [C, H, W]
    acts = activations[0][0]       # shape: [C, H, W]
    weights = grads.mean(dim=(1, 2))  # shape: [C]

    # Weighted combination of activation maps
    cam = torch.zeros(acts.shape[1:], dtype=acts.dtype)  # [H, W]
    for i, w in enumerate(weights):
        cam += w * acts[i]

    # ReLU and normalize
    cam = F.relu(cam)
    if cam.max() > 0:
        cam = cam / cam.max()
    cam = cam.cpu().numpy()

    # Resize CAM to original image dimensions
    original_image = Image.open(image_path).convert("RGB")
    cam_resized = np.array(
        Image.fromarray((cam * 255).astype(np.uint8)).resize(
            original_image.size, resample=Image.BILINEAR
        )
    ) / 255.0

    # Apply jet colormap to CAM
    heatmap_colored = cm.jet(cam_resized)[:, :, :3]  # drop alpha channel

    # Blend: overlay heatmap on original image
    original_arr = np.array(original_image).astype(np.float32) / 255.0
    blended = 0.55 * heatmap_colored + 0.45 * original_arr
    blended = np.clip(blended, 0, 1)

    # Save the blended heatmap image
    out_path = Path(settings.heatmap_dir) / f"{uuid.uuid4().hex}.png"
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


def run_ensemble(image_path: str, disease_key: str) -> Dict:
    loader = RegistryModelLoader(settings.model_registry_path)
    registry = loader.load_registry()
    disease_entry = registry[disease_key]

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)

    weighted_probs = None
    class_names = None
    last_model = None

    for model_key, info in disease_entry["models"].items():
        model, current_class_names, meta = loader.load_model(disease_key, model_key)
        probs = torch.softmax(model(tensor), dim=1).detach().cpu().numpy()[0]
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

    # Generate real Grad-CAM heatmap using the last loaded model
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
        "heatmap_url": f"/static/heatmaps/{Path(heatmap_path).name}",
        "report_url": None,
    }
