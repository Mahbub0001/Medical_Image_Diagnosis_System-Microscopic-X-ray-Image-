# Graph Report - cap_software_2.0  (2026-09-19)

## Corpus Check
- 59 files · ~23,538,433 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 451 nodes · 673 edges · 34 communities (30 shown, 4 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 35 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c2f4bd3d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_BloodDetect AI — Medical Image Diagnosis System|BloodDetect AI — Medical Image Diagnosis System]]
- [[_COMMUNITY_prediction.py|prediction.py]]
- [[_COMMUNITY_routers.py|routers.py]]
- [[_COMMUNITY_inference.py|inference.py]]
- [[_COMMUNITY_auth.py|auth.py]]
- [[_COMMUNITY_package.json|package.json]]
- [[_COMMUNITY_client.js|client.js]]
- [[_COMMUNITY_App.jsx|App.jsx]]
- [[_COMMUNITY_11.2 Pages & Features|11.2 Pages & Features]]
- [[_COMMUNITY_5.1 API Endpoints|5.1 API Endpoints]]
- [[_COMMUNITY_6. Database Schema|6. Database Schema]]
- [[_COMMUNITY_BloodDetect AI Project Pack|BloodDetect AI Project Pack]]
- [[_COMMUNITY_graphify|graphify.md]]
- [[_COMMUNITY_graphify|graphify.md]]
- [[_COMMUNITY_ReportsPage.jsx|ReportsPage.jsx]]
- [[_COMMUNITY_vercel.json|vercel.json]]
- [[_COMMUNITY_routers.py|routers.py]]
- [[_COMMUNITY_Hugging Face Migration — Agent Prompt|Hugging Face Migration — Agent Prompt]]
- [[_COMMUNITY_model_inference.py|model_inference.py]]
- [[_COMMUNITY_BloodDetect AI — System Specifications & Workflows|BloodDetect AI — System Specifications & Workflows]]
- [[_COMMUNITY_🩺 BloodDetect AI — Comprehensive Project Specification & Overview|🩺 BloodDetect AI — Comprehensive Project Specification & Overview]]
- [[_COMMUNITY_🩺 BloodDetect AI — Comprehensive Project Specification & Overview|🩺 BloodDetect AI — Comprehensive Project Specification & Overview]]
- [[_COMMUNITY_model_loader.py|model_loader.py]]

## God Nodes (most connected - your core abstractions)
1. `BloodDetect AI — Medical Image Diagnosis System` - 17 edges
2. `Prediction` - 15 edges
3. `generate_combined_report()` - 15 edges
4. `RegistryModelLoader` - 12 edges
5. `generate_text_report()` - 11 edges
6. `analyze_image()` - 10 edges
7. `analyze_comprehensive()` - 10 edges
8. `run_ensemble()` - 10 edges
9. `run_blood_ensemble_prediction()` - 9 edges
10. `Hugging Face Migration — Agent Prompt` - 9 edges

## Surprising Connections (you probably didn't know these)
- `DummyBranch` --uses--> `RegistryModelLoader`  [INFERRED]
  huggingface_space/inference.py → backend/app/ml/model_loader.py
- `FullEnsembleModel` --uses--> `RegistryModelLoader`  [INFERRED]
  huggingface_space/inference.py → backend/app/ml/model_loader.py
- `TrueMultiNet5` --uses--> `RegistryModelLoader`  [INFERRED]
  huggingface_space/inference.py → backend/app/ml/model_loader.py
- `run_image_routing_check()` --calls--> `_load_lung_router_fresh()`  [INFERRED]
  backend/app/ml/routers.py → huggingface_space/routers.py
- `admin_summary()` --indirect_call--> `Prediction`  [INFERRED]
  backend/app/api/routes/admin.py → backend/app/db/models.py

## Import Cycles
- None detected.

## Communities (34 total, 4 thin omitted)

### Community 0 - "BloodDetect AI — Medical Image Diagnosis System"
Cohesion: 0.04
Nodes (47): 10.1 Report Sections, 10.2 Report Styling, 10. PDF Report Generation, 12.1 Backend Deployment (Render), 12.2 Frontend Deployment (Vercel), 12.3 Dockerfile Details, 12. Deployment Architecture, 13. Complete File Structure (+39 more)

### Community 1 - "prediction.py"
Cohesion: 0.13
Nodes (30): analyze_comprehensive(), analyze_image(), background_sync_batch(), background_sync_single(), clinical_suggestion(), delete_temp_file(), download_combined_report(), download_report() (+22 more)

### Community 2 - "routers.py"
Cohesion: 0.10
Nodes (13): clear_router_cache(), ConvBnActLung, DSConvBlockBlood, DSConvBlockLung, _get_blood_router_cached(), Validates if the image matches the selected diagnostic domain.     Returns: (is, No-op: router models are no longer cached. Kept for API compatibility., ResidualDSBlockBlood (+5 more)

### Community 3 - "inference.py"
Cohesion: 0.12
Nodes (18): certainty_label(), clinical_suggestion(), DummyBranch, FullEnsembleModel, generate_ensemble_gradcam_heatmap(), generate_fallback_heatmap(), generate_gradcam_heatmap(), generate_yolo_gradcam_heatmap() (+10 more)

### Community 4 - "auth.py"
Cohesion: 0.13
Nodes (19): admin_summary(), Session, login(), Session, register(), Settings, create_access_token(), get_password_hash() (+11 more)

### Community 5 - "package.json"
Cohesion: 0.11
Nodes (17): dependencies, axios, react, react-dom, react-router-dom, recharts, devDependencies, vite (+9 more)

### Community 6 - "client.js"
Cohesion: 0.15
Nodes (16): api, COLORS, PredictionSummaryChart(), COLORS, StatsCards(), LungXrayPage(), FindingPanel(), formatFileSize() (+8 more)

### Community 7 - "App.jsx"
Cohesion: 0.20
Nodes (10): App(), DashboardPage, HistoryPage, UploadPage, AppLayout(), links, Sidebar(), ThemeContext (+2 more)

### Community 8 - "11.2 Pages & Features"
Cohesion: 0.17
Nodes (12): 11.1 Application Structure, 11.2 Pages & Features, 11.3 UI Design System, 11.4 Routing, 11. Frontend Application, Blood Smear Upload Page (Microscope Image Classifier), Color Palette, Dashboard Page (+4 more)

### Community 9 - "5.1 API Endpoints"
Cohesion: 0.25
Nodes (8): 5.1 API Endpoints, 5.2 Prediction Workflow (End-to-End), 5.3 CORS Configuration, 5. Backend API Specification, Admin Routes (`/admin`), Authentication Routes (`/auth`), Prediction Routes (`/predict`), Static File Routes

### Community 10 - "6. Database Schema"
Cohesion: 0.17
Nodes (16): certainty_label(), clinical_suggestion(), DummyBranch, FullEnsembleModel, generate_ensemble_gradcam_heatmap(), generate_fallback_heatmap(), generate_gradcam_heatmap(), generate_yolo_gradcam_heatmap() (+8 more)

### Community 11 - "BloodDetect AI Project Pack"
Cohesion: 0.40
Nodes (4): BloodDetect AI Project Pack, Recommended next steps, Run backend, Run frontend

### Community 14 - "ReportsPage.jsx"
Cohesion: 0.21
Nodes (21): _disclaimer_block(), generate_combined_report(), generate_text_report(), _get_heatmap_flowable(), _make_page_decorator(), _make_stat_cell(), _make_styles(), _prob_table() (+13 more)

### Community 27 - "routers.py"
Cohesion: 0.10
Nodes (13): predict(), UploadFile, ConvBnActLung, DSConvBlockBlood, DSConvBlockLung, _load_blood_router_fresh(), _load_lung_router_fresh(), ResidualDSBlockBlood (+5 more)

### Community 28 - "Hugging Face Migration — Agent Prompt"
Cohesion: 0.10
Nodes (19): 3a. Update requirements.txt, 3b. Add HF Space URL to config.py, 3c. Create new service: backend/app/services/hf_inference.py, 3d. Modify inference.py, 3e. Modify prediction.py, 3f. Update routers.py, app.py for the Space, Files to Create (+11 more)

### Community 29 - "model_inference.py"
Cohesion: 0.15
Nodes (11): DummyBranch, FullEnsembleModel, load_model(), predict(), Ensemble model inference module — 8-class blood disease classifier. Replaces the, Wraps MultiNet-A/B/C and combines their softmax outputs by weighted average., # IMPORTANT: the saved checkpoint itself contains a (buggy, equal-weighted), image_path_or_pil: file path (str) OR an already-opened PIL.Image     Returns: { (+3 more)

### Community 30 - "BloodDetect AI — System Specifications & Workflows"
Cohesion: 0.14
Nodes (13): 1.1 Decoupled Components, 1. System Architecture, 2.1 Frontend Image Compression, 2.2 Hugging Face Space (ML Engine), 2.3 Render Backend (Gateway), 2. Component Specifications, 3.1 AI Analysis & Diagnosis Pipeline, 3. Core Workflows (+5 more)

### Community 31 - "🩺 BloodDetect AI — Comprehensive Project Specification & Overview"
Cohesion: 0.12
Nodes (16): 📌 1. Executive Summary & Core Mission, 🏗️ 2. Dual-Mode Architecture & Cloud Stack, 🧠 3. Machine Learning Models & Deep Pipelines, 🔍 4. Explainable AI (Grad-CAM Visualizations), 📑 5. Professional Medical Report Architecture, 📋 6. Summary Matrix of System Core Features, 8 Canonical Blood Classes:, A. Dual Execution Modes (+8 more)

### Community 32 - "🩺 BloodDetect AI — Comprehensive Project Specification & Overview"
Cohesion: 0.12
Nodes (16): 📌 1. Executive Summary & Core Mission, 🏗️ 2. Dual-Mode Architecture & Cloud Stack, 🧠 3. Machine Learning Models & Deep Pipelines, 🔍 4. Explainable AI (Grad-CAM Visualizations), 📑 5. Professional Medical Report Architecture, 📋 6. Summary Matrix of System Core Features, 8 Canonical Blood Classes:, A. Dual Execution Modes (+8 more)

## Knowledge Gaps
- **126 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+121 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_image_routing_check()` connect `routers.py` to `prediction.py`, `routers.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `_load_lung_router_fresh()` connect `routers.py` to `routers.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `RegistryModelLoader` connect `inference.py` to `6. Database Schema`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Prediction` (e.g. with `admin_summary()` and `background_sync_batch()`) actually correct?**
  _`Prediction` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `RegistryModelLoader` (e.g. with `DummyBranch` and `FullEnsembleModel`) actually correct?**
  _`RegistryModelLoader` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Uploads files to Cloudinary in background and updates DB with permanent cloud UR`, `Uploads batch of comprehensive panel files to Cloudinary in background thread po`, `Re-generate and serve the combined PDF for a Comprehensive Blood Panel session.` to the rest of the system?**
  _149 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `BloodDetect AI — Medical Image Diagnosis System` be split into smaller, more focused modules?**
  _Cohesion score 0.041666666666666664 - nodes in this community are weakly interconnected._