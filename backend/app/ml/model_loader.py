import json
from pathlib import Path
from typing import Dict, Tuple
import torch
import torch.nn as nn
from torchvision import models

def build_resnet18(num_classes: int):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model

def build_mobilenet_v3_small(num_classes: int):
    model = models.mobilenet_v3_small(weights=None)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)
    return model

def build_efficientnet_b0(num_classes: int):
    model = models.efficientnet_b0(weights=None)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)
    return model

BUILDERS = {
    "resnet18": build_resnet18,
    "mobilenet_v3_small": build_mobilenet_v3_small,
    "efficientnet_b0": build_efficientnet_b0,
}

class RegistryModelLoader:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
        self.cache: Dict[str, Dict] = {}

    def load_registry(self):
        if not self.registry_path.exists():
            return {}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def load_model(self, disease_key: str, model_key: str):
        registry = self.load_registry()
        entry = registry[disease_key]["models"][model_key]
        class_names = entry["class_names"]
        builder = BUILDERS[entry["builder"]]
        model = builder(len(class_names))
        weights_path = entry["weights_path"]
        # Resolve weights path relative to the backend directory
        backend_dir = self.registry_path.parent.parent.parent
        full_weights_path = backend_dir / weights_path
        state = torch.load(full_weights_path, map_location="cpu")
        model.load_state_dict(state)
        model.eval()
        return model, class_names, entry
