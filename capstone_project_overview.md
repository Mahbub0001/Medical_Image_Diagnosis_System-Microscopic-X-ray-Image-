# 🔬 BioLens — Comprehensive Project Specification & Technical Overview

**Capstone Project Technical Specification, Architecture & Clinical Workflow Reference**

---

## 📌 1. Executive Summary & Core Mission

**BioLens** is an advanced, full-stack medical AI diagnosis and clinical decision support system designed specifically for clinical pathologists, hematologists, and healthcare professionals. The platform delivers automated, explainable, high-precision disease classification and comprehensive diagnostic report generation across two major diagnostic domains:

1. **Microscopic Blood Smear Analysis**:
   - **Malaria**: *Plasmodium* Parasitized vs. Uninfected / Healthy blood cells.
   - **Anemia**: Anemic RBC morphological abnormality vs. Normal / Healthy RBCs.
   - **Acute Lymphoblastic Leukemia (ALL)**: 4 distinct cellular malignancy stages (`Benign`, `Early Pre-B`, `Pre-B`, `Pro-B`).
   - **Flexible Multi-Disease Screening (Comprehensive Blood Panel)**: Ability to upload and screen 1, 2, or 3 diseases simultaneously for a single patient with a unified diagnostic master report.

2. **Chest Radiography (Pulmonary X-Ray)**:
   - Automated screening for `Normal`, `Pneumonia`, and `Tuberculosis (TB)`.

By combining a **3-Stream Fusion MultiNet Deep Ensemble model (9 fused vision backbones)** with **Grad-CAM visual explainability**, **automated domain validation routing**, **phone-number-based patient longitudinal history tracking**, and a **hybrid Local/Cloud execution architecture**, BioLens provides real-time, clinically actionable diagnostics with **>96% test confidence**.

---

## 🏗️ 2. Dual-Mode Architecture & Cloud Stack

The system supports a **flexible dual-runtime execution model**, allowing seamless transition between standalone offline deployment (100% local resources) and cloud-scale live production:

```
[User Browser / Client (React 18 + Vite)]
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend API Gateway: FastAPI (Python 3.11)                  │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
    [Local Execution Mode]          [Live / Cloud Mode]
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│ Local PyTorch Inference      │ │ Hugging Face Space (GPU)    │
│ • Local ensemble_model.pth   │ │ • Remote ML Server          │
│ • 100% offline & private     │ │ • Zero Render RAM pressure  │
└──────────────┬───────────────┘ └─────────────┬───────────────┘
               │                               │
               └───────────────┬───────────────┘
                               ▼
        ┌──────────────────────────────────────────────┐
        │ Cloud Persistence & Asset Infrastructure     │
        │ • Supabase PostgreSQL (Patient Records & DB)│
        │ • Cloudinary Media CDN (Images & Heatmaps)   │
        └──────────────────────────────────────────────┘
```

### A. Dual Execution Modes

| Feature / Mode | 💻 100% Local Mode (Offline / Desktop) | 🌐 Live Cloud Mode (Production) |
|---|---|---|
| **Configuration** | `HF_SPACE_URL` commented out in `.env` | `HF_SPACE_URL` enabled in Environment |
| **Inference Engine** | Local PyTorch running `ensemble_model.pth` | Dedicated Hugging Face Space ML Server |
| **Cloud Resource Use** | Zero Hugging Face quota / resources used | Offloads heavy computation to 16GB GPU Space |
| **Pathologist Benefit** | Instant local response, zero latency, data privacy | Globally accessible without local GPU hardware |

### B. Frontend Presentation Layer
- **Framework**: React 18.3.1 + Vite 5.4.2 SPA (hosted on **Vercel**).
- **Core Views & Modules**:
  - `UploadPage.jsx`: 
    - **Dual Mode Toggle**: `Single Test` (quick 1-image evaluation) vs `Comprehensive Panel` (multi-disease hematology screening).
    - **Interactive Test Chips**: Toggle Anemia, Malaria, and Leukemia dynamically.
    - **Per-Disease Upload Slots**: Independent drag-and-drop slots with instant client-side canvas compression (`imageCompressor.js`).
    - **Interactive Result Panels**: Color-coded findings per disease, certainty indicators, Grad-CAM heatmap view buttons, and 1-click **Download Combined Report (PDF)**.
  - `LungXrayPage.jsx`: Chest radiograph diagnostic interface with automated domain pre-validation and heatmap visualizations.
  - `DashboardPage.jsx`: Real-time pathology analytics, longitudinal charts, and diagnostic distribution metrics.
  - `HistoryPage.jsx`: Patient-centric longitudinal record logs with phone number search, individual test details, and direct PDF report downloads.

### C. Backend API Gateway Layer
- **Framework**: Python 3.11 + FastAPI (containerized via Docker on **Render**).
- **Core Endpoints & Services**:
  - `POST /predict/analyze`: Single image inference for blood smears or chest X-rays.
  - `POST /predict/analyze-comprehensive`: Multi-part endpoint accepting 1–3 blood disease images, running ensemble inference per image, saving database records with session tags, and returning aggregated findings + combined PDF report URL.
  - `GET /predict/combined-report/{id}`: On-demand reconstruction and retrieval of combined hematology PDF reports from historical sessions.
  - `GET /predict/history` & `GET /predict/patient/{phone_number}`: Longitudinal query endpoints.
  - `auth.py`: JWT authentication (`python-jose`) with bcrypt password hashing (`passlib`).
  - `image_validation.py`: Laplacian variance blur analysis and domain pre-checks.
  - `report_service.py`: Automated professional clinical PDF report compilation via ReportLab with header bands, risk badges, probability tables, and disclaimers.

### D. Data Storage & Cloud CDN
- **Supabase (PostgreSQL)**: AWS `ap-northeast-1` relational database storing user accounts, patient records, phone numbers, multi-class confidence vectors, certainty levels, and report endpoints.
- **Cloudinary CDN**: Automated cloud storage for raw patient uploads (`biolens/uploads`) and generated Grad-CAM overlays (`biolens/heatmaps`). Local temporary files are automatically purged post-upload.

---

## 🧠 3. Machine Learning Models & Deep Pipelines

### 🛡️ A. Image Domain Router & Quality Validator (`routers.py`)
- **Architecture**: Domain Routing ConvNet + OpenCV Sharpness Analysis.
- **Function**: Automatically validates whether an uploaded image matches `blood` smear or `lung` X-ray characteristics, rejecting invalid uploads (e.g. non-medical images or out-of-focus slides).

---

### 🩸 B. Blood Smear Master Model (`FullEnsembleModel`)
The microscopic blood smear diagnosis is powered by a **3-Stream Fusion MultiNet Deep Ensemble** comprising **9 state-of-the-art vision backbones**:

1. **MultiNet-A** ($w_A = 0.3344$, 1536 fused features):
   - `poolformer_s24` (MetaFormer pooling architecture)
   - `mobilevit_s` (Lightweight hybrid Vision Transformer)
   - `xcit_small_12_p16_224` (Cross-Covariance Image Transformer)
2. **MultiNet-B** ($w_B = 0.3325$, 3200 fused features):
   - `poolformer_s24` (Spatial pooling)
   - `mobilevit_s` (Mobile ViT)
   - `resnet101d` (Deep residual network with tweak D)
3. **MultiNet-C** ($w_C = 0.3331$, 4224 fused features):
   - `poolformer_s24` (Pooling Transformer)
   - `densenet169` (Dense feature-reuse network)
   - `resnet101d` (Deep residual backbone)

#### Softmax Ensemble Voting Formulation:
\[
P_{\text{ensemble}}(y=k \mid \mathbf{x}) = \sum_{m \in \{A, B, C\}} w_m \cdot \text{Softmax}\left(\mathbf{z}_m(\mathbf{x})\right)_k
\]
Where $\sum w_m = 1.0$ ($w_A = 0.3344, w_B = 0.3325, w_C = 0.3331$).

#### 8 Canonical Blood Classes:
1. `anemic` — Red Blood Cell morphology indicative of Anemia
2. `non_anemic` — Healthy, normocytic normochromic RBCs
3. `benign_leukemia` — Non-malignant leukocyte controls
4. `early_leukemia` — Early stage Acute Lymphoblastic Leukemia
5. `pre_leukemia` — Pre-B Acute Lymphoblastic Leukemia
6. `pro_leukemia` — Pro-B Acute Lymphoblastic Leukemia
7. `parasitized` — *Plasmodium* infected erythrocyte (Malaria positive)
8. `non_parasitized` — Uninfected erythrocyte (Malaria negative)

---

### 🫁 C. Chest Radiograph (Lung X-Ray Section)
- **Model Architecture**: ResNet-18 Deep Convolutional Neural Network.
- **Classes**: `Normal`, `Pneumonia`, `Tuberculosis`.

---

## 🔍 4. Explainable AI (Grad-CAM Visualizations)

To ensure clinical transparency and pathologist interpretability:
- **Algorithm**: Gradient-weighted Class Activation Mapping (Grad-CAM) hooked into final convolutional feature maps.
- **Clinical Artifacts**:
  1. **Raw Microscopic Slide**: Unprocessed cell image.
  2. **Heatmap Activation**: Colormap highlighting high-gradient diagnostic regions.
  3. **Blended Composite**: 55% Jet Colormap + 45% Original Slide for direct visual correlation.

\[
\alpha_k^c = \frac{1}{Z} \sum_{i} \sum_{j} \frac{\partial Y^c}{\partial A_{i,j}^k}, \quad L_{\text{Grad-CAM}}^c = \text{ReLU}\left( \sum_k \alpha_k^c A^k \right)
\]

---

## 📑 5. Professional Medical Report Architecture

BioLens includes an automated, publication-grade PDF generation engine powered by ReportLab:

1. **Brand Header Band**: Dark professional header with BioLens typography, generation timestamp, and unique report reference ID (`RPT-...` or `COMB-...`).
2. **Patient Demographics Block**: Clean tabular format displaying Patient Name, Phone / Patient ID, and Analysis Date.
3. **Executive Summary & Risk Badges**: Color-coded risk indicators (`High Risk`, `Moderate Risk`, `Review Needed`, `Low Risk`) and summary metric cards.
4. **Diagnostic Panels & Probability Breakdown**: Sectioned disease findings with exact confidence percentages, certainty ratings, and formatted class score tables.
5. **Clinical Recommendations & Action Items**: Contextual medical suggestions based on detected abnormalities.
6. **Regulatory Disclaimer & Page Numbering**: Standard clinical AI research disclaimer and automated page numbers.

---

## 📋 6. Summary Matrix of System Core Features

| Feature Component | Microscopic Blood Smear Section | Chest Radiograph (Lung X-Ray) Section |
|---|---|---|
| **Diagnostic Target** | Malaria, Anemia, Leukemia (4 stages) | Normal, Pneumonia, Tuberculosis |
| **Classes Supported** | 8 Canonical Classes | 3 Classes (`Normal`, `Pneumonia`, `TB`) |
| **Model Architecture** | `FullEnsembleModel` (9 Fused Backbones) | ResNet-18 Deep Convolutional Backbone |
| **Ensemble Accuracy** | **>96.5% Test Accuracy / Confidence** | **>95% Test Accuracy** |
| **Explainability** | MultiNet Target Layer Grad-CAM Overlay | ResNet-18 Layer-4 Grad-CAM Overlay |
| **Multi-Image Screening**| Comprehensive Blood Panel (1–3 disease images) | Single X-ray Analysis |
| **Patient Identification**| Name + Mobile Phone Number (`phone_number`) | Name + Mobile Phone Number (`phone_number`) |
| **Execution Modes** | Dual: 100% Local PyTorch / Hugging Face Space | Dual: 100% Local PyTorch / Hugging Face Space |
| **Database Integration**| Supabase PostgreSQL (`Prediction` records) | Supabase PostgreSQL (`Prediction` records) |
| **Media Cloud Storage** | Cloudinary CDN (`biolens/` buckets) | Cloudinary CDN (`biolens/` buckets) |
| **Report Generation** | Automated Single & Combined PDF Reports | Automated Single PDF Diagnostic Report |
