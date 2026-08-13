# Graph Report - cap_software_2.0  (2026-08-10)

## Corpus Check
- 58 files · ~363,790 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 388 nodes · 551 edges · 31 communities (28 shown, 3 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `890acf49`
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
- [[_COMMUNITY_vercel.json|vercel.json]]
- [[_COMMUNITY_routers.py|routers.py]]
- [[_COMMUNITY_Hugging Face Migration — Agent Prompt|Hugging Face Migration — Agent Prompt]]
- [[_COMMUNITY_model_inference.py|model_inference.py]]
- [[_COMMUNITY_BloodDetect AI — System Specifications & Workflows|BloodDetect AI — System Specifications & Workflows]]

## God Nodes (most connected - your core abstractions)
1. `BloodDetect AI — Medical Image Diagnosis System` - 17 edges
2. `RegistryModelLoader` - 12 edges
3. `Prediction` - 11 edges
4. `analyze_image()` - 10 edges
5. `run_ensemble()` - 9 edges
6. `Hugging Face Migration — Agent Prompt` - 9 edges
7. `run_blood_ensemble_prediction()` - 8 edges
8. `run_blood_ensemble_prediction()` - 8 edges
9. `run_ensemble()` - 8 edges
10. `register()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `DummyBranch` --uses--> `RegistryModelLoader`  [INFERRED]
  huggingface_space/inference.py → backend/app/ml/model_loader.py
- `FullEnsembleModel` --uses--> `RegistryModelLoader`  [INFERRED]
  huggingface_space/inference.py → backend/app/ml/model_loader.py
- `TrueMultiNet5` --uses--> `RegistryModelLoader`  [INFERRED]
  huggingface_space/inference.py → backend/app/ml/model_loader.py
- `admin_summary()` --indirect_call--> `Prediction`  [INFERRED]
  backend/app/api/routes/admin.py → backend/app/db/models.py
- `predict()` --calls--> `run_ensemble()`  [INFERRED]
  huggingface_space/app.py → huggingface_space/inference.py

## Import Cycles
- None detected.

## Communities (31 total, 3 thin omitted)

### Community 0 - "BloodDetect AI — Medical Image Diagnosis System"
Cohesion: 0.04
Nodes (47): 10.1 Report Sections, 10.2 Report Styling, 10. PDF Report Generation, 12.1 Backend Deployment (Render), 12.2 Frontend Deployment (Vercel), 12.3 Dockerfile Details, 12. Deployment Architecture, 13. Complete File Structure (+39 more)

### Community 1 - "prediction.py"
Cohesion: 0.12
Nodes (26): analyze_image(), clinical_suggestion(), delete_temp_file(), download_report(), format_db_url(), get_patient_history_by_phone(), get_prediction_detail(), get_prediction_history() (+18 more)

### Community 2 - "routers.py"
Cohesion: 0.10
Nodes (14): clear_router_cache(), ConvBnActLung, DSConvBlockBlood, DSConvBlockLung, _load_blood_router_fresh(), _load_lung_router_fresh(), Load the blood router model without caching. Caller is responsible for cleanup., Load the lung router model without caching. Caller is responsible for cleanup. (+6 more)

### Community 3 - "inference.py"
Cohesion: 0.11
Nodes (18): certainty_label(), clinical_suggestion(), DummyBranch, FullEnsembleModel, generate_ensemble_gradcam_heatmap(), generate_fallback_heatmap(), generate_gradcam_heatmap(), generate_yolo_gradcam_heatmap() (+10 more)

### Community 4 - "auth.py"
Cohesion: 0.14
Nodes (18): admin_summary(), Session, login(), Session, register(), Settings, create_access_token(), get_password_hash() (+10 more)

### Community 5 - "package.json"
Cohesion: 0.11
Nodes (17): dependencies, axios, react, react-dom, react-router-dom, recharts, devDependencies, vite (+9 more)

### Community 6 - "client.js"
Cohesion: 0.21
Nodes (8): api, COLORS, PredictionSummaryChart(), COLORS, StatsCards(), LungXrayPage(), UploadPage(), compressImage()

### Community 7 - "App.jsx"
Cohesion: 0.17
Nodes (12): App(), DashboardPage, HistoryPage, LungXrayPage, ReportsPage, UploadPage, AppLayout(), links (+4 more)

### Community 8 - "11.2 Pages & Features"
Cohesion: 0.17
Nodes (12): 11.1 Application Structure, 11.2 Pages & Features, 11.3 UI Design System, 11.4 Routing, 11. Frontend Application, Blood Smear Upload Page (Microscope Image Classifier), Color Palette, Dashboard Page (+4 more)

### Community 9 - "5.1 API Endpoints"
Cohesion: 0.25
Nodes (8): 5.1 API Endpoints, 5.2 Prediction Workflow (End-to-End), 5.3 CORS Configuration, 5. Backend API Specification, Admin Routes (`/admin`), Authentication Routes (`/auth`), Prediction Routes (`/predict`), Static File Routes

### Community 10 - "6. Database Schema"
Cohesion: 0.11
Nodes (17): certainty_label(), clinical_suggestion(), DummyBranch, FullEnsembleModel, generate_ensemble_gradcam_heatmap(), generate_fallback_heatmap(), generate_gradcam_heatmap(), generate_yolo_gradcam_heatmap() (+9 more)

### Community 11 - "BloodDetect AI Project Pack"
Cohesion: 0.40
Nodes (4): BloodDetect AI Project Pack, Recommended next steps, Run backend, Run frontend

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

## Knowledge Gaps
- **102 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+97 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `predict()` connect `routers.py` to `6. Database Schema`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `RegistryModelLoader` connect `inference.py` to `6. Database Schema`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `RegistryModelLoader` (e.g. with `DummyBranch` and `FullEnsembleModel`) actually correct?**
  _`RegistryModelLoader` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Prediction` (e.g. with `admin_summary()` and `download_report()`) actually correct?**
  _`Prediction` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Get prediction history, optionally filtered by user_id or phone_number, with pag`, `Get detailed information about a specific prediction`, `Get all past prediction records for a specific patient phone number` to the rest of the system?**
  _118 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `BloodDetect AI — Medical Image Diagnosis System` be split into smaller, more focused modules?**
  _Cohesion score 0.041666666666666664 - nodes in this community are weakly interconnected._
- **Should `prediction.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12258064516129032 - nodes in this community are weakly interconnected._