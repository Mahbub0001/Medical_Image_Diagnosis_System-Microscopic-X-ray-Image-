# 🩺 BloodDetect AI — Comprehensive Project Specification & Overview

**Capstone Project Technical Overview & Architecture Reference**

---

## 📌 1. Executive Summary & Core Mission

**BloodDetect AI** is a full-stack, AI-powered medical image diagnosis platform designed for automated disease classification and explainable diagnostic reporting. The system processes two primary medical image domains:

1. **Microscopic Blood Smear Slides** (Malaria, Anemia, and 4-stage Leukemia classification).
2. **Chest Radiographs / X-Rays** (Normal, Pneumonia, and Tuberculosis classification).

By coupling a **3-stream MultiNet Deep Ensemble model** with **Grad-CAM visual explainability**, **automated domain/quality routing**, and **cloud-offloaded microservices**, BloodDetect AI provides real-time predictions without overloading lightweight hosting environments.

---

## 🏗️ 2. Microservices Architecture & Cloud Stack

```
[User Browser / Client]
       │
       ▼
┌──────────────────────────────────────────┐
│ 1. Frontend: React 18 + Vite (Vercel)    │  ◄── Single Page Application
└────────────────────┬─────────────────────┘
                     │ HTTP REST Requests
                     ▼
┌──────────────────────────────────────────┐
│ 2. Backend API Gateway: FastAPI (Render) │  ◄── Docker Container (Python 3.11)
└──────────┬───────────────────┬───────────┘
           │                   │
    (GPU Proxy Request)        │ (Persistence & Assets)
           │                   │
           ▼                   ▼
┌───────────────────────┐  ┌─────────────────────────────┐
│ 3. ML GPU Inference:  │  │ 4. Storage & Infrastructure:│
│ Hugging Face Space    │  │ • Supabase PostgreSQL (DB)  │
│ (16GB vRAM / GPU)     │  │ • Cloudinary Media CDN      │
└───────────────────────┘  └─────────────────────────────┘
```

### A. Frontend Presentation Layer
- **Framework**: React 18.3.1 + Vite 5.4.2 SPA hosted on **Vercel**.
- **User Interface Pages**:
  - `UploadPage.jsx`: Microscopic blood smear upload, drag-and-drop, and client-side image compression (`imageCompressor.js`).
  - `LungXrayPage.jsx`: Chest radiograph upload and processing.
  - `DashboardPage.jsx`: Real-time analytics, metrics, and Recharts pie chart visualization.
  - `HistoryPage.jsx`: Patient-centric prediction logs and phone number filtering.
  - `ReportsPage.jsx`: PDF report generation and download portal.

### B. Backend API Gateway Layer
- **Framework**: Python 3.11 + FastAPI hosted on **Render** (containerized via Docker).
- **Core Microservices**:
  - `auth.py`: JWT token authentication (`python-jose`) and bcrypt password hashing (`passlib`).
  - `prediction.py`: Request handler, proxy routing, and real-time database transactions.
  - `image_validation.py`: Quality validation (aspect ratio, resolution, and Laplacian variance sharpness checks).
  - `report_service.py`: ReportLab dynamic medical PDF report compilation.

### C. Cloud AI Machine Learning Tier
- **Environment**: **Hugging Face Space** (16GB vRAM / GPU enabled).
- **Rationale**: Heavy deep learning model inference (786 MB ensemble weight) is offloaded from Render to Hugging Face Space, preventing Out-Of-Memory (OOM) server crashes on Render.
- **Auto Model Weights Fetching**: Automatically fetches model weights from Hugging Face Hub (`Mahbub0001/blood-ensemble-model`) if not found locally.

### D. Data Storage & Asset Management
- **Supabase (PostgreSQL)**: AWS ap-northeast-1 hosted relational database storing user credentials, prediction records, confidence metrics, and report endpoints.
- **Cloudinary CDN**: Media storage for uploaded raw images and generated Grad-CAM heatmap overlays.

---

## 🧠 3. Machine Learning Models & Deep Pipelines

### 🛡️ A. Image Domain Router & Quality Validator (`routers.py`)
- **Architecture**: Domain Routing ConvNet + OpenCV Blur Analysis.
- **Function**: Automatically validates whether an uploaded image matches `blood` smear or `lung` X-ray characteristics, rejecting invalid uploads (e.g. non-medical images or out-of-focus slides).

---

### 🩸 B. Blood Smear Section (8-Class Master Model)
- **Model Architecture**: `FullEnsembleModel` (3-Stream MultiNet Deep Ensemble).
- **Backbone Fusion (9 Deep Networks)**:
  1. **MultiNet-A** ($w_A = 0.3344$): PoolFormer-S24 + MobileViT-S + XCiT-Small-12
  2. **MultiNet-B** ($w_B = 0.3325$): PoolFormer-S24 + MobileViT-S + ResNet-101d
  3. **MultiNet-C** ($w_C = 0.3331$): PoolFormer-S24 + DenseNet-169 + ResNet-101d
- **Diseases & 8 Supported Classes**:
  - **Malaria**: `Parasitized`, `Uninfected`
  - **Anemia**: `Anemic`, `Normal`
  - **Leukemia**: `Benign`, `Early`, `Pre`, `Pro`
- **Softmax Ensemble Voting Formula**:

\[
P_{\text{ensemble}}(y=k \mid \mathbf{x}) = w_A P_A(y=k \mid \mathbf{x}) + w_B P_B(y=k \mid \mathbf{x}) + w_C P_C(y=k \mid \mathbf{x})
\]

---

### 🫁 C. Chest Radiograph (Lung X-Ray Section)
- **Model Architecture**: ResNet-18 Deep Convolutional Neural Network.
- **Diseases & 3 Supported Classes**: `Normal`, `Pneumonia`, `Tuberculosis`.

---

## 🔍 4. Explainable AI (Grad-CAM Visualizations)

- **Algorithm**: Gradient-weighted Class Activation Mapping hooked to target convolutional layers (`layer4` / final `Conv2d`).
- **3-Panel Output**:
  1. **Original Image**: Raw input image.
  2. **Grad-CAM Activation**: Gradient-weighted activation map.
  3. **Blended Overlay**: 55% Jet Colormap + 45% Original Image.

\[
\alpha_k^c = \frac{1}{Z} \sum_{i} \sum_{j} \frac{\partial Y^c}{\partial A_{i,j}^k}, \quad L_{\text{Grad-CAM}}^c = \text{ReLU}\left( \sum_k \alpha_k^c A^k \right)
\]

---

## 📄 5. Summary Matrix of System Core Features

| Feature Component | Microscopic Blood Smear Section | Chest Radiograph (Lung X-Ray) Section |
|---|---|---|
| **Diagnostic Target** | Malaria, Anemia, Leukemia (4 stages) | Normal, Pneumonia, Tuberculosis |
| **Classes Supported** | 8 Classes (`anemic`, `parasitized`, `pre`, etc.) | 3 Classes (`Normal`, `Pneumonia`, `TB`) |
| **Model Architecture** | `FullEnsembleModel` (MultiNet-A/B/C) | ResNet-18 Convolutional Backbone |
| **Explainability** | MultiNet Target Layer Grad-CAM Overlay | ResNet-18 Layer-4 Grad-CAM Overlay |
| **Model Weights Fetch** | Hugging Face Hub (`Mahbub0001/blood-ensemble-model`) | Local Registry / HF Model Hub |
| **Report Generation** | Dynamic ReportLab PDF with Heatmap Asset | Dynamic ReportLab PDF with Heatmap Asset |
