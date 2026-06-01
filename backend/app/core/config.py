from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "BloodDetect AI API"
    debug: bool = True
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./blooddetect.db"
    upload_dir: str = "storage/uploads"
    report_dir: str = "storage/reports"
    heatmap_dir: str = "storage/heatmaps"
    model_registry_path: str = "app/ml/registry.json"
    
    # Cloudinary Configs (Optional, falls back to local static storage if not set)
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
