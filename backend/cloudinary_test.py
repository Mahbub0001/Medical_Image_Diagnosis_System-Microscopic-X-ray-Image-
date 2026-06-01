import cloudinary
import cloudinary.uploader
import cloudinary.api

# 1. Configure Cloudinary inline
cloudinary.config(
    cloud_name="dre2ynekk",
    api_key="585847932276486",
    api_secret="5a0JSAOXAg3pkF2POxYvzq2syls",
    secure=True
)

# 2. Upload a sample image from Cloudinary's demo domain
sample_url = "https://res.cloudinary.com/demo/image/upload/dog.jpg"
print(f"Uploading sample image from: {sample_url}")
upload_result = cloudinary.uploader.upload(sample_url)

secure_url = upload_result.get("secure_url")
public_id = upload_result.get("public_id")
print("Upload Successful!")
print(f"Secure URL: {secure_url}")
print(f"Public ID: {public_id}")

# 3. Get image details/metadata
print("\nFetching image details...")
details = cloudinary.api.resource(public_id)
print(f"Width: {details.get('width')} px")
print(f"Height: {details.get('height')} px")
print(f"Format: {details.get('format')}")
print(f"File Size: {details.get('bytes')} bytes")

# 4. Transform the image URL
# f_auto: Automatically selects the best image format based on the requesting browser (e.g. WebP, AVIF)
# q_auto: Automatically optimizes the quality of the image to compress file size while keeping visual quality high
transformed_url = cloudinary.utils.cloudinary_url(
    public_id,
    transformation=[
        {"fetch_format": "auto", "quality": "auto"}
    ]
)[0]

print("\nDone! Click link below to see optimized version of the image. Check the size and the format.")
print(transformed_url)
