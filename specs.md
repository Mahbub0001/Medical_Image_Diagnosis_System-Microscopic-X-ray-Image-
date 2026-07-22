# BloodDetect AI — System Specifications & Workflows

This document outlines the detailed system specifications, file structures, integration workflows, and execution pipelines of **BloodDetect AI** (version 2.0).

---

## 1. System Architecture

The project is structured as a distributed, decoupled full-stack medical application to accommodate machine learning models under constrained free-tier hosting limits.

```
       [ Client Browser (React Single Page App hosted on Vercel) ]
                                   │
                                   │ (HTTP / FormData / JWT Auth)
                                   ▼
             [ Backend Gateway (FastAPI hosted on Render) ]
               │                 │                  │
       (Save)  │         (Proxy) │          (Store) │
               ▼                 ▼                  ▼
     [ Supabase DB ]     [ Hugging Face Space ]  [ Cloudinary CDN ]
     (PostgreSQL)        (Docker ML Server)      (Image Storage)
```

### 1.1 Decoupled Components
1. **Frontend (Vercel)**: Built with **React 18 + Vite 5**. Handles UI/UX, user states, dashboard analytics, client-side file compression, and report downloads.
2. **Backend Controller (Render)**: Built with **FastAPI**. Manages authentication (JWT + bcrypt), API gateways, database transactions, PDF report generation via ReportLab, and proxies ML requests.
3. **ML Inference Engine (Hugging Face Space)**: A **Dockerized FastAPI server** running on the Hugging Face Free CPU tier (16GB RAM). Houses PyTorch model weights, executes domain routing, performs class inference, and computes Grad-CAM heatmaps.
4. **Cloud Database (Supabase)**: A hosted PostgreSQL instance storing users, diagnostic reports, and analytics metadata.
5. **Cloud Storage (Cloudinary)**: A media CDN storing original slide/X-ray uploads and generated Grad-CAM heatmaps.

---

## 2. Component Specifications

### 2.1 Frontend Image Compression
To prevent upload timeouts and save bandwidth, the frontend intercepts any image file selection:
* **Trigger Threshold**: File size > **200 KB**.
* **Method**: Draws the image onto a temporary HTML5 Canvas, resizing the maximum dimension (width or height) to **1024px** while preserving the aspect ratio.
* **Compression**: Exports the canvas as an `image/jpeg` blob with **85% quality** (converting RGBA safely to RGB by clearing the alpha channel).

### 2.2 Hugging Face Space (ML Engine)
Running inside a lightweight Linux container (`python:3.10-slim`):
* **CPU Optimized PyTorch**: Explicitly installs `torch` and `torchvision` from the CPU-only index (`https://download.pytorch.org/whl/cpu`) to keep the container under 1.5GB.
* **OpenCV Support**: Includes `libgl1` and `libglib2.0-0` Debian dependencies required by OpenCV and Ultralytics YOLOv11s.
* **Inference Endpoint**: Exposes `/predict` receiving `file` (image) and `disease_key`.

### 2.3 Render Backend (Gateway)
* **Lightweight Container**: Completely excludes `torch`, `torchvision`, and `matplotlib` from its dependencies. Startup RAM footprint is **< 40MB**, guaranteeing zero OOM (Out Of Memory) crashes.
* **Hybrid Fallback Logic**: If the `HF_SPACE_URL` environment variable is missing, it dynamically falls back to local PyTorch loaders (enabling fully offline localhost development).

---

## 3. Core Workflows

### 3.1 AI Analysis & Diagnosis Pipeline
The diagram below describes the sequence of actions when a user uploads a medical image for analysis:

```
[UI / Page]             [Compressor]             [Render API]            [HF ML Space]          [Cloud Services]
    │                         │                        │                       │                       │
    │ 1. Upload File          │                        │                       │                       │
    │────────────────────────>│                        │                       │                       │
    │                         │ 2. Resize & Compress   │                       │                       │
    │                         │    (If > 200KB)        │                       │                       │
    │ 3. Submit Form (FormData)                        │                       │                       │
    │─────────────────────────────────────────────────>│                       │                       │
    │                         │                        │ 4. Forward Image      │                       │
    │                         │                        │──────────────────────>│                       │
    │                         │                        │                       │ 5. Validate Domain    │
    │                         │                        │                       │ 6. Run Inference      │
    │                         │                        │                       │ 7. Generate Grad-CAM  │
    │                         │                        │                       │ 8. Convert to Base64  │
    │                         │                        │ 9. Return JSON Data   │                       │
    │                         │                        │<──────────────────────│                       │
    │                         │                        │    (Class + Base64)   │                       │
    │                         │                        │                       │                       │
    │                         │                        │ 10. Write Heatmap     │                       │
    │                         │                        │ 11. Upload Images     │                       │
    │                         │                        │──────────────────────────────────────────────>│
    │                         │                        │                       │   (Save to Cloudinary)│
    │                         │                        │ 12. Save Metadata     │                       │
    │                         │                        │──────────────────────────────────────────────>│
    │                         │                        │                       │    (Save to Supabase) │
    │                         │                        │ 13. Return Response   │                       │
    │<─────────────────────────────────────────────────│                       │                       │
```

1. **Upload & Selection**: The user selects a blood smear or X-ray image in `UploadPage.jsx` or `LungXrayPage.jsx`.
2. **Client Compression**: If the file exceeds 200KB, `imageCompressor.js` downscales it to 1024px JPEG.
3. **API Submission**: React posts the file, patient name, and disease key to Render `/predict/analyze`.
4. **ML Delegate**: FastAPI proxies the files to the Hugging Face Space `/predict` endpoint.
5. **Image Verification**: Hugging Face runs `run_image_routing_check` using a custom lightweight `RoutingNet` / `RoutingCNN` to verify the image type (smear vs. X-ray).
6. **AI Inference**: Runs `run_ensemble` (ResNet-18 or YOLOv11s depending on the disease).
7. **Explainability Map**: Computes the gradients on the final conv layer of the network to draw the Grad-CAM activation map and saves it as a temporary PNG.
8. **Base64 Packaging**: Converts the heatmap PNG into a Base64-encoded string and deletes the temporary PNG file to prevent disk fill-up.
9. **Proxy Return**: Hugging Face sends the classification classes, confidence scores, risk metrics, and the Base64 heatmap back to Render.
10. **File Reconstruction**: Render decodes the Base64 string back into a local PNG file.
11. **Cloud CDN Upload**: Uploads both the original input image and the decoded Grad-CAM heatmap to Cloudinary.
12. **Metadata Persist**: Saves the diagnostic findings, risk levels, and CDN URLs to the PostgreSQL database on Supabase.
13. **UI Update**: Returns the classification probabilities and URLs to Vercel, rendering interactive charts and allowing report downloads.

---

## 4. Models Configuration

The system uses a total of 8 machine learning models:

| Key | Model Type | Architecture | Weight File | Target Classes |
|---|---|---|---|---|
| `router` | Domain Router | RoutingCNN | `routing_best_blood.pth` | `anemia_rbc`, `invalid`, `leukemia_wbc`, `malaria_rbc` |
| `router_lung`| Domain Router | RoutingNet | `routing_best_lungs.pth` | `valid`, `invalid` (Lungs) |
| `malaria` | Blood Smear | ResNet-18 | `resnet18_malaria.pth` | `Parasitized`, `Uninfected` |
| `anemia` | Blood Smear | ResNet-18 | `resnet18_anemia.pth` | `Anemic`, `Normal` |
| `leukemia` | Blood Smear | ResNet-18 | `resnet18_leukemia_corrected.pth` | `Benign`, `Early`, `Pre`, `Pro` |
| `lung` | Lung X-Ray | ResNet-18 | `resnet18_lung.pth` | `Normal`, `Pneumonia`, `Tuberculosis` |
| `blood` | Combined Blood| YOLOv11s-cls| `blood_combined_yolo_11s.pt`| Combined blood disease categories |

---

## 5. Development and Setup Configuration

### 5.1 Local Offline Mode
Run the backend with your local Python environment:
1. Do not define `HF_SPACE_URL` in `backend/.env`.
2. Make sure `torch`, `torchvision`, `matplotlib`, and `ultralytics` are installed in your local python virtual environment.
3. Start uvicorn:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```
4. Start React frontend:
   ```bash
   cd frontend
   npm run dev
   ```

### 5.2 Lightweight Production Mode (Render + Hugging Face)
1. Build and push the backend to Render.
2. In the Render Dashboard under **Environment Variables**, add `HF_SPACE_URL` (pointing to your Hugging Face Space app link, e.g., `https://mahbub0001-medical-image-classifier.hf.space`).
3. Render will route all ML workloads to your Space, requiring no machine learning libraries on Render.
