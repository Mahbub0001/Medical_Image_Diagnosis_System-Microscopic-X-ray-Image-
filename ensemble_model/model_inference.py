"""
Ensemble model inference module — 8-class blood disease classifier.
Replaces the old YOLO model in the website backend.

WHAT THIS NEEDS FROM YOU (place next to this file, or update the paths below):
    - ensemble_model.pth   (the 786 MB master weight file from Kaggle)

INSTALL (once):
    pip install torch torchvision timm==0.9.12 pillow

USAGE:
    from model_inference import predict
    result = predict("path/to/image.jpg")
    # result -> {"class": "parasitized", "confidence": 0.97, "probabilities": {...}}
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import timm

# ---------------------------------------------------------------------------
# 1. CONFIG — must exactly match training-time settings, don't change these
# ---------------------------------------------------------------------------
IMG_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# This EXACT order was asserted against CANONICAL_CLASS_ORDER in the notebook
# (== sorted(EXPECTED_CLASSES)). Index i here = the i-th output of the model.
CLASS_NAMES = [
    "anemic",
    "benign_leukemia",
    "early_leukemia",
    "non_anemic",
    "non_parasitized",
    "parasitized",
    "pre_leukemia",
    "pro_leukemia",
]
NUM_CLASSES = len(CLASS_NAMES)

# *** IMPORTANT — FIX THE WEIGHT BUG FROM THE NOTEBOOK ***
# In the Kaggle notebook (cell 21), FullEnsembleModel() was created WITHOUT
# passing the computed `weights` array from cell 12 — so the saved
# ensemble_model.pth currently has equal 1/3-1/3-1/3 weighting baked in,
# NOT your validated "weighted voting" weights.
#
# Real weights from your notebook's cell 12 output (weighted-voting, by val accuracy):
#   MultiNet-A (multi-1-2-4) acc=0.9759  weight=0.3344
#   MultiNet-B (multi-1-2-5) acc=0.9704  weight=0.3325
#   MultiNet-C (multi-1-3-5) acc=0.9722  weight=0.3331
ENSEMBLE_WEIGHTS = [0.3344, 0.3325, 0.3331]  # MultiNet-A, B, C -- already filled in, no edit needed

MODEL_WEIGHTS_PATH = "ensemble_model.pth"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---------------------------------------------------------------------------
# 2. MODEL ARCHITECTURE — copied from the training notebook, must match
#    exactly or the .pth weights won't load correctly.
# ---------------------------------------------------------------------------
class DummyBranch(nn.Module):
    """Fallback branch used only if a timm backbone fails to build."""

    def __init__(self, out_features=512):
        super().__init__()
        self.out_features = out_features

    def forward(self, x):
        return torch.zeros(x.shape[0], self.out_features, device=x.device)


class TrueMultiNet5(nn.Module):
    """Fusion of 3 timm backbones -> concatenated features -> classifier head."""

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
                    dummy_out = branch(torch.zeros(1, 3, IMG_SIZE, IMG_SIZE))
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
    """Wraps MultiNet-A/B/C and combines their softmax outputs by weighted average."""

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


# ---------------------------------------------------------------------------
# 3. PREPROCESSING — must match training exactly (same resize + normalize)
# ---------------------------------------------------------------------------
preprocess = transforms.Compose(
    [
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ]
)


# ---------------------------------------------------------------------------
# 4. LOAD MODEL ONCE (module-level, so the website doesn't reload it per request)
# ---------------------------------------------------------------------------
_model = None


def load_model():
    global _model
    if _model is None:
        print(f"Loading ensemble model on {DEVICE} ...")
        model = FullEnsembleModel(num_classes=NUM_CLASSES, weights=ENSEMBLE_WEIGHTS)
        state_dict = torch.load(MODEL_WEIGHTS_PATH, map_location=DEVICE)
        model.load_state_dict(state_dict)

        # IMPORTANT: the saved checkpoint itself contains a (buggy, equal-weighted)
        # "weights" buffer from the original notebook, so load_state_dict() just
        # silently overwrote our ENSEMBLE_WEIGHTS above with 1/3-1/3-1/3. Force the
        # correct weights back in *after* loading, so they actually take effect.
        with torch.no_grad():
            model.weights.copy_(torch.tensor(ENSEMBLE_WEIGHTS, dtype=torch.float32))

        model.to(DEVICE)
        model.eval()
        _model = model
        print("Model loaded successfully.")
    return _model


# ---------------------------------------------------------------------------
# 5. PREDICT — the function your website backend should call
# ---------------------------------------------------------------------------
@torch.no_grad()
def predict(image_path_or_pil):
    """
    image_path_or_pil: file path (str) OR an already-opened PIL.Image
    Returns: {"class": str, "confidence": float, "probabilities": {class_name: prob}}
    """
    model = load_model()

    if isinstance(image_path_or_pil, str):
        img = Image.open(image_path_or_pil).convert("RGB")
    else:
        img = image_path_or_pil.convert("RGB")

    input_tensor = preprocess(img).unsqueeze(0).to(DEVICE)
    probs = model(input_tensor)[0].cpu().numpy()

    pred_idx = int(probs.argmax())
    return {
        "class": CLASS_NAMES[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {CLASS_NAMES[i]: float(probs[i]) for i in range(NUM_CLASSES)},
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python model_inference.py <image_path>")
    else:
        result = predict(sys.argv[1])
        print(result)
