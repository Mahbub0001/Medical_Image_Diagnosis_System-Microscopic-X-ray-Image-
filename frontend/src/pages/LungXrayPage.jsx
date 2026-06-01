import React, { useState } from "react";
import { api } from "../api/client";

export default function LungXrayPage() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [patientName, setPatientName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const onFileChange = (e) => {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    if (selectedFile) {
      setPreviewUrl(URL.createObjectURL(selectedFile));
    } else {
      setPreviewUrl("");
    }
  };

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
      formData.append("disease_key", "lung");

      const response = await api.post("/predict/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(response.data);
    } catch (err) {
      setError(
        err?.response?.data?.detail?.message ||
          err?.response?.data?.detail ||
          "Prediction failed."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Lung X-Ray Classifier</h2>
        <p>Upload a chest X-ray image to detect Pneumonia, Tuberculosis, or Normal findings.</p>
      </div>

      <div className="card">
        <form onSubmit={onSubmit} className="upload-form">
          <label>
            Patient Name
            <input
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              placeholder="Enter patient name"
            />
          </label>

          <label className="file-input">
            Select X-Ray Image
            <input type="file" accept=".jpg,.jpeg,.png" onChange={onFileChange} />
          </label>

          {previewUrl && (
            <div style={{ marginTop: "10px", textAlign: "center" }}>
              <p style={{ fontWeight: 600, marginBottom: "8px" }}>Selected Image Preview:</p>
              <img
                src={previewUrl}
                alt="Preview"
                style={{
                  maxWidth: "100%",
                  maxHeight: "300px",
                  borderRadius: "12px",
                  border: "1px solid var(--border)",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                }}
              />
            </div>
          )}

          <button className="primary-btn" disabled={loading || !file} style={{ marginTop: "8px" }}>
            {loading ? "Analyzing X-Ray..." : "Upload & Analyze"}
          </button>
        </form>
      </div>

      {error ? <div className="error-box">{error}</div> : null}

      {result ? (
        <div className="result-grid">
          <div className="card" style={{ borderLeft: "5px solid var(--primary)" }}>
            <h3>Prediction Result</h3>
            <p><strong>Category:</strong> {result.predicted_disease}</p>
            <p>
              <strong>Detected Finding:</strong>{" "}
              <span
                style={{
                  color:
                    result.predicted_class.toLowerCase() === "normal"
                      ? "green"
                      : "var(--danger)",
                  fontWeight: "bold",
                }}
              >
                {result.predicted_class}
              </span>
            </p>
            <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
            <p><strong>Certainty:</strong> {result.certainty}</p>
            <p><strong>Risk Level:</strong> {result.risk_level}</p>
            <p><strong>Suggestion:</strong> {result.suggestion}</p>
          </div>

          <div className="card">
            <h3>Class Probabilities</h3>
            <div style={{ display: "grid", gap: "10px", marginTop: "12px" }}>
              {Object.entries(result.probabilities).map(([className, score]) => (
                <div key={className}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 500 }}>{className}</span>
                    <span>{(score * 100).toFixed(2)}%</span>
                  </div>
                  <div
                    style={{
                      height: "8px",
                      background: "#e5e7eb",
                      borderRadius: "4px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${score * 100}%`,
                        background:
                          className.toLowerCase() === "normal" ? "#22c55e" : "#ef4444",
                        borderRadius: "4px",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>Diagnostic Resources</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
              {result.heatmap_url ? (
                <a
                  href={result.heatmap_url.startsWith("http") ? result.heatmap_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${result.heatmap_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="primary-btn"
                  style={{ textAlign: "center", textDecoration: "none", color: "white" }}
                >
                  View Heatmap Analysis
                </a>
              ) : (
                <p>No heatmap available</p>
              )}
              {result.report_url ? (
                <a
                  href={result.report_url.startsWith("http") ? result.report_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${result.report_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="primary-btn"
                  style={{
                    textAlign: "center",
                    textDecoration: "none",
                    color: "white",
                    background: "linear-gradient(90deg, #10b981, #059669)",
                  }}
                >
                  Download Text Report
                </a>
              ) : (
                <p>No report available</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
