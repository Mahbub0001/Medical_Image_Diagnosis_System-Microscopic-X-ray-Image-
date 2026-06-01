from PIL import Image
import numpy as np

def estimate_blur_score(pil_image: Image.Image) -> float:
    arr = np.array(pil_image.convert("L"), dtype=np.float32)
    return float(arr.var())

def validate_uploaded_image(file_path: str):
    image = Image.open(file_path).convert("RGB")
    width, height = image.size
    blur_score = estimate_blur_score(image)

    errors = []
    if width < 100 or height < 100:
        errors.append("Image resolution is too low.")
    if blur_score < 100.0:
        errors.append("Image looks blurry.")
    return {
        "valid": len(errors) == 0,
        "width": width,
        "height": height,
        "blur_score": blur_score,
        "errors": errors,
    }
