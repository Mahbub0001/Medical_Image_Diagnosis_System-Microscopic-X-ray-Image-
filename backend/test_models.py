import sys
from pathlib import Path

# Add backend directory to path so we can import app modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from app.ml.model_loader import RegistryModelLoader
    print("Successfully imported RegistryModelLoader")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

loader = RegistryModelLoader("app/ml/registry.json")
registry = loader.load_registry()
print(f"Registered disease keys: {list(registry.keys())}\n")

all_ok = True
for disease_key, info in registry.items():
    print(f"Disease: {info.get('display_name', disease_key)} ({disease_key})")
    for model_key in info.get("models", {}):
        print(f"  Loading model: {model_key}...")
        try:
            model, class_names, entry = loader.load_model(disease_key, model_key)
            print(f"    [OK] Loaded weights: {entry['weights_path']}")
            print(f"    [OK] Registered Class Names: {class_names}")
            # Run a dummy input tensor of shape (1, 3, 224, 224) through the model to verify forward pass
            import torch
            dummy_input = torch.randn(1, 3, 224, 224)
            output = model(dummy_input)
            print(f"    [OK] Forward pass output shape: {list(output.shape)}")
            if output.shape[1] != len(class_names):
                print(f"    [ERROR] Mismatch between model output logits ({output.shape[1]}) and registered class name count ({len(class_names)})!")
                all_ok = False
        except Exception as e:
            print(f"    [FAILED] Error: {e}")
            all_ok = False
    print("-" * 50)

if all_ok:
    print("\nAll models loaded and verified successfully!")
    sys.exit(0)
else:
    print("\nSome models failed verification. Please review the errors above.")
    sys.exit(1)
