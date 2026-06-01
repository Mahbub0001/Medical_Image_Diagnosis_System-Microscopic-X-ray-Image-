# BloodDetect AI Project Pack

This package contains:

1. **Improved Jupyter notebook**
   - `BloodDetect_AI_Improved_Notebook.ipynb`

2. **Backend (FastAPI)**
   - Authentication
   - Image validation
   - Prediction endpoint
   - Report generation
   - Static file serving

3. **Frontend (React + Vite)**
   - Dashboard
   - Upload page
   - History page
   - Reports page

## Recommended next steps
- Copy your trained `.pth` model files into `backend/models/`
- Create `backend/app/ml/registry.json` from `registry.example.json`
- Replace placeholder heatmap generation with real Grad-CAM output
- Add JWT-protected routes
- Add PostgreSQL if you move beyond local development

## Run backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run frontend
```bash
cd frontend
npm install
npm run dev
```
