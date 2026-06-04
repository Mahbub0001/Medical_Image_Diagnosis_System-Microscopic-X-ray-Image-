import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from pathlib import Path
from ..core.config import settings

# --- Paths to Router Weights ---
registry_path = Path(settings.model_registry_path).resolve()
backend_dir = registry_path.parent.parent.parent
workspace_dir = backend_dir.parent

BLOOD_ROUTER_WEIGHTS = workspace_dir / "routing_best_blood.pth"
LUNG_ROUTER_WEIGHTS = workspace_dir / "routing_best_lungs.pth"

# ============================================================
# BLOOD ROUTER: RoutingCNN (Input Size: 224x224)
# ============================================================

class SEBlockBlood(nn.Module):
    def __init__(self, channels, reduction=16):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(channels, max(channels // reduction, 4)),
            nn.ReLU(inplace=True),
            nn.Linear(max(channels // reduction, 4), channels),
            nn.Sigmoid()
        )

    def forward(self, x):
        scale = self.se(x).view(x.size(0), x.size(1), 1, 1)
        return x * scale


class DSConvBlockBlood(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.dw = nn.Sequential(
            nn.Conv2d(in_ch, in_ch, 3, stride=stride, padding=1, groups=in_ch, bias=False),
            nn.BatchNorm2d(in_ch),
            nn.ReLU6(inplace=True),
        )
        self.pw = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU6(inplace=True),
        )
        self.se = SEBlockBlood(out_ch)

    def forward(self, x):
        return self.se(self.pw(self.dw(x)))


class ResidualDSBlockBlood(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.block = DSConvBlockBlood(in_ch, out_ch, stride)
        self.skip = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 1, stride=stride, bias=False),
            nn.BatchNorm2d(out_ch)
        ) if (in_ch != out_ch or stride != 1) else nn.Identity()

    def forward(self, x):
        return self.block(x) + self.skip(x)


class RoutingCNN(nn.Module):
    def __init__(self, num_classes=2, drop=0.4):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, 7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU6(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
        )
        self.block1 = ResidualDSBlockBlood(32, 64, stride=1)
        self.block2 = nn.Sequential(
            ResidualDSBlockBlood(64, 128, stride=2),
            ResidualDSBlockBlood(128, 128, stride=1),
        )
        self.block3 = nn.Sequential(
            ResidualDSBlockBlood(128, 256, stride=2),
            ResidualDSBlockBlood(256, 256, stride=1),
        )
        self.block4 = nn.Sequential(
            ResidualDSBlockBlood(256, 512, stride=2),
            ResidualDSBlockBlood(512, 512, stride=1),
        )
        self.gap  = nn.AdaptiveAvgPool2d(1)
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(drop),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.gap(x)
        return self.head(x)


# ============================================================
# LUNG ROUTER: RoutingNet (Input Size: 128x128)
# ============================================================

class SEBlockLung(nn.Module):
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        scale = self.se(x).view(x.size(0), x.size(1), 1, 1)
        return x * scale


class DSConvBlockLung(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.dw = nn.Conv2d(in_ch, in_ch, kernel_size=3, stride=stride, padding=1, groups=in_ch, bias=False)
        self.pw = nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.act = nn.SiLU(inplace=True)

    def forward(self, x):
        return self.act(self.bn(self.pw(self.dw(x))))


class ConvBnActLung(nn.Module):
    def __init__(self, in_ch, out_ch, kernel=3, stride=1, padding=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel, stride=stride, padding=padding, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.SiLU(inplace=True)
        )

    def forward(self, x):
        return self.block(x)


class RoutingNet(nn.Module):
    def __init__(self, num_classes=2, dropout=0.4):
        super().__init__()
        self.stem = ConvBnActLung(3, 32, stride=2)
        self.stage1 = nn.Sequential(
            DSConvBlockLung(32,  64,  stride=2),
            ConvBnActLung(64, 64),
        )
        self.stage2 = nn.Sequential(
            DSConvBlockLung(64,  128, stride=2),
            ConvBnActLung(128, 128),
            SEBlockLung(128, reduction=8),
        )
        self.stage3 = nn.Sequential(
            DSConvBlockLung(128, 256, stride=2),
            ConvBnActLung(256, 256),
            SEBlockLung(256, reduction=16),
        )
        self.stage4 = nn.Sequential(
            DSConvBlockLung(256, 512, stride=2),
            ConvBnActLung(512, 512),
            SEBlockLung(512, reduction=16),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(p=dropout),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.stage4(x)
        return self.head(x)


# ============================================================
# Caching and Inference logic
# ============================================================

_blood_router_cache = None
_lung_router_cache = None

def load_blood_router():
    global _blood_router_cache
    if _blood_router_cache is None:
        model = RoutingCNN(num_classes=2)
        state_dict = torch.load(BLOOD_ROUTER_WEIGHTS, map_location="cpu", weights_only=False)
        model.load_state_dict(state_dict)
        model.eval()
        _blood_router_cache = model
    return _blood_router_cache


def load_lung_router():
    global _lung_router_cache
    if _lung_router_cache is None:
        model = RoutingNet(num_classes=2)
        state_dict = torch.load(LUNG_ROUTER_WEIGHTS, map_location="cpu", weights_only=False)
        model.load_state_dict(state_dict)
        model.eval()
        _lung_router_cache = model
    return _lung_router_cache


def run_image_routing_check(image_path: str, disease_key: str) -> tuple:
    """
    Validates if the image matches the selected diagnostic domain.
    Returns: (is_valid: bool, error_message: str)
    """
    if disease_key == "blood":
        if not BLOOD_ROUTER_WEIGHTS.exists():
            return True, ""  # Graceful bypass if weights missing
            
        model = load_blood_router()
        img = Image.open(image_path).convert("RGB")
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            out = model(tensor)
            pred = out.argmax(dim=1).item()
        
        # 1 means valid, 0 means invalid
        if pred == 1:
            return True, ""
        else:
            return False, "Invalid image. Please provide a valid blood smear image."

    elif disease_key == "lung":
        if not LUNG_ROUTER_WEIGHTS.exists():
            return True, ""  # Graceful bypass if weights missing
            
        model = load_lung_router()
        img = Image.open(image_path).convert("RGB")
        transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            out = model(tensor)
            pred = out.argmax(dim=1).item()
            
        # 1 means valid, 0 means invalid
        if pred == 1:
            return True, ""
        else:
            return False, "Invalid image. Please provide a valid chest X-ray image."

    return True, ""
