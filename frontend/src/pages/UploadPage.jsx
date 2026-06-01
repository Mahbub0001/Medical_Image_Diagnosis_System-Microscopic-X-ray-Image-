import React, { useState } from "react";
import { api } from "../api/client";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [patientName, setPatientName] = useState("");
  const [diseaseKey, setDiseaseKey] = useState("malaria");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("patient_name", patientName || "User");
      formData.append("disease_key", diseaseKey);

      const response = await api.post("/predict/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || "Prediction failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Upload Blood Image</h2>
        <p>Upload a microscope blood-smear image for AI-based analysis.</p>
      </div>

      <div className="card">
        <form onSubmit={onSubmit} className="upload-form">
          <label>
            Patient Name
            <input value={patientName} onChange={(e) => setPatientName(e.target.value)} placeholder="Enter patient name" />
          </label>

          <label>
            Model Group
            <select value={diseaseKey} onChange={(e) => setDiseaseKey(e.target.value)}>
              <option value="malaria">Malaria</option>
              <option value="anemia">Anemia</option>
              <option value="leukemia">Leukemia</option>
            </select>
          </label>

          <label className="file-input">
            Select Image
            <input type="file" accept=".jpg,.jpeg,.png" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>

          <button className="primary-btn" disabled={loading}>
            {loading ? "Processing..." : "Upload & Analyze"}
          </button>
        </form>
      </div>

      {error ? <div className="error-box">{error}</div> : null}

      {result ? (
        <div className="result-grid">
          <div className="card">
            <h3>Prediction Result</h3>
            <p><strong>Disease:</strong> {result.predicted_disease}</p>
            <p><strong>Class:</strong> {result.predicted_class}</p>
            <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
            <p><strong>Certainty:</strong> {result.certainty}</p>
            <p><strong>Risk:</strong> {result.risk_level}</p>
            <p><strong>Suggestion:</strong> {result.suggestion}</p>
          </div>

          <div className="card">
            <h3>Probabilities</h3>
            <pre>{JSON.stringify(result.probabilities, null, 2)}</pre>
          </div>

          <div className="card">
            <h3>Explainability / Report</h3>
            {result.heatmap_url ? (
              <a
                href={result.heatmap_url.startsWith("http") ? result.heatmap_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${result.heatmap_url}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Heatmap
              </a>
            ) : (
              <p>No heatmap</p>
            )}
            <br />
            {result.report_url ? (
              <a
                href={result.report_url.startsWith("http") ? result.report_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${result.report_url}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Report
              </a>
            ) : (
              <p>No report</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
