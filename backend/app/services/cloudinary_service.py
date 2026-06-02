import cloudinary
import cloudinary.uploader
from pathlib import Path
from ..core.config import settings

# Configure Cloudinary if credentials are provided
cloudinary_enabled = False
if settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )
    cloudinary_enabled = True

def upload_file_to_cloudinary(file_path: str, folder: str = "blooddetect") -> str:
    """
    Uploads a file to Cloudinary and returns its secure URL.
    Falls back to returning a local static server path if Cloudinary is not configured.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if cloudinary_enabled:
        # Determine resource type (raw for pdf/txt reports, image for jpg/png)
        resource_type = "auto"
        if p.suffix.lower() in (".txt", ".pdf"):
            resource_type = "raw"
            
        result = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            resource_type=resource_type
        )
        return result.get("secure_url")
    else:
        # Local fallback path: convert internal path to web static URL
        # e.g., backend/storage/uploads/x.png -> /static/uploads/x.png
        parent_name = p.parent.name  # uploads, heatmaps, or reports
        return f"/static/{parent_name}/{p.name}"
