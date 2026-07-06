import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from pathlib import Path

# --- Paths to Router Weights in HF Space ---
BLOOD_ROUTER_WEIGHTS = Path("models/routing_best_blood.pth")
LUNG_ROUTER_WEIGHTS = Path("models/routing_best_lungs.pth")

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
        w = self.se(x)
        return x * w.unsqueeze(-1).unsqueeze(-1)


class ConvBnActBlood(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.conv(x)


class DSConvBlockBlood(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.dw = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, kernel_size=3, stride=stride, padding=1, groups=in_channels, bias=False),
            nn.BatchNorm2d(in_channels),
            nn.ReLU(inplace=True)
        )
        self.pw = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.pw(self.dw(x))


class RoutingCNN(nn.Module):
    def __init__(self, num_classes=2, dropout=0.3):
        super().__init__()
        self.stem = ConvBnActBlood(3, 32, stride=2)
        self.stage1 = nn.Sequential(
            DSConvBlockBlood(32, 64),
            ConvBnActBlood(64, 64),
            SEBlockBlood(64)
        )
        self.stage2 = nn.Sequential(
            DSConvBlockBlood(64, 128, stride=2),
            ConvBnActBlood(128, 128),
            SEBlockBlood(128)
        )
        self.stage3 = nn.Sequential(
            DSConvBlockBlood(128, 256, stride=2),
            ConvBnActBlood(256, 256),
            SEBlockBlood(256)
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(p=dropout),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        return self.head(x)


# ============================================================
# LUNGS ROUTER: RoutingNet (Input Size: 128x128)
# ============================================================

class SEBlockLung(nn.Module):
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
        w = self.se(x)
        return x * w.unsqueeze(-1).unsqueeze(-1)


class ConvBnActLung(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.conv(x)


class DSConvBlockLung(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.dw = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, kernel_size=3, stride=stride, padding=1, groups=in_channels, bias=False),
            nn.BatchNorm2d(in_channels),
            nn.ReLU(inplace=True)
        )
        self.pw = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.pw(self.dw(x))


class RoutingNet(nn.Module):
    def __init__(self, num_classes=2, dropout=0.4):
        super().__init__()
        self.stem = ConvBnActLung(3, 32, stride=2)
        self.stage1 = nn.Sequential(
            DSConvBlockLung(32, 64),
            ConvBnActLung(64, 64),
            SEBlockLung(64, reduction=16),
        )
        self.stage2 = nn.Sequential(
            DSConvBlockLung(64, 128, stride=2),
            ConvBnActLung(128, 128),
            SEBlockLung(128, reduction=16),
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
# Standalone Fresh Loaders
# ============================================================

def _load_blood_router_fresh():
    model = RoutingCNN(num_classes=2)
    state_dict = torch.load(BLOOD_ROUTER_WEIGHTS, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    for param in model.parameters():
        param.requires_grad = False
    return model


def _load_lung_router_fresh():
    model = RoutingNet(num_classes=2)
    state_dict = torch.load(LUNG_ROUTER_WEIGHTS, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    for param in model.parameters():
        param.requires_grad = False
    return model


def run_image_routing_check(image_path: str, disease_key: str) -> tuple:
    import gc

    if disease_key == "blood":
        if not BLOOD_ROUTER_WEIGHTS.exists():
            return True, ""  # Graceful bypass if weights missing

        model = _load_blood_router_fresh()
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

        del model
        gc.collect()

        if pred == 1:
            return True, ""
        else:
            return False, "Invalid image. Please provide a valid blood smear image."

    elif disease_key == "lung":
        if not LUNG_ROUTER_WEIGHTS.exists():
            return True, ""  # Graceful bypass if weights missing

        model = _load_lung_router_fresh()
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

        del model
        gc.collect()

        if pred == 1:
            return True, ""
        else:
            return False, "Invalid image. Please provide a valid chest X-ray image."

    return True, ""
