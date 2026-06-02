import React, { useState, useEffect } from "react";
import { api } from "../api/client";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [patientName, setPatientName] = useState("");
  const [diseaseKey, setDiseaseKey] = useState("malaria");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Processing...");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    let interval;
    if (loading) {
      const messages = [
        "Uploading microscopic smear to pipeline...",
        "Validating cell aspect ratios and colors...",
        "Evaluating structures via ResNet-18 model...",
        "Running prediction ensemble check...",
        "Synthesizing Grad-CAM explainability map...",
        "Generating final medical PDF report..."
      ];
      let i = 0;
      setLoadingMessage(messages[0]);
      interval = setInterval(() => {
        i = (i + 1) % messages.length;
        setLoadingMessage(messages[i]);
      }, 1300);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selectedFile = e.dataTransfer.files[0];
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
    }
  };

  const onFileChange = (e) => {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    if (selectedFile) {
      setPreviewUrl(URL.createObjectURL(selectedFile));
    } else {
      setPreviewUrl("");
    }
  };

  const clearSelection = () => {
    setFile(null);
    setPreviewUrl("");
    setResult(null);
    setError("");
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
      formData.append("disease_key", diseaseKey);

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

  const getBarColor = (className) => {
    const c = className.toLowerCase();
    if (["normal", "uninfected", "benign"].includes(c)) {
      return "var(--success)";
    }
    if (["parasitized", "anemic", "pro", "early"].includes(c)) {
      return "var(--danger)";
    }
    return "var(--warning)";
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "";
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Microscope Image Classifier</h2>
        <p>Upload blood-smear slide samples to detect Malaria, Anemia, or Leukemia abnormalities.</p>
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

          <label>
            Diagnostic Target Key
            <select value={diseaseKey} onChange={(e) => setDiseaseKey(e.target.value)}>
              <option value="malaria">Malaria Smear</option>
              <option value="anemia">Anemia RBC</option>
              <option value="leukemia">Leukemia WBC</option>
            </select>
          </label>

          <div style={{ display: "grid", gap: "8px" }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "#cbd5e1" }}>Slide Smear Image</span>
            
            {!file ? (
              <div 
                className={`drop-zone ${dragActive ? "dragover" : ""}`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => document.getElementById("file-select").click()}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                <div>
                  <p style={{ margin: "0 0 4px 0", fontWeight: 700, color: "#ffffff" }}>Drag & drop sample image here</p>
                  <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)" }}>or click to browse from system (JPG, PNG)</p>
                </div>
                <input 
                  id="file-select" 
                  type="file" 
                  accept=".jpg,.jpeg,.png" 
                  onChange={onFileChange} 
                  style={{ display: "none" }} 
                />
              </div>
            ) : (
              <div className="card" style={{ background: "rgba(255,255,255,0.02)", padding: "16px", display: "flex", alignItems: "center", gap: "16px", border: "1px dashed var(--border)" }}>
                {previewUrl && (
                  <img
                    src={previewUrl}
                    alt="Preview"
                    style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "10px", border: "1px solid var(--border)" }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: "0 0 4px 0", fontWeight: 600, color: "#ffffff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</p>
                  <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--muted)" }}>Size: {formatFileSize(file.size)}</p>
                </div>
                <button type="button" className="primary-btn" onClick={clearSelection} style={{ padding: "8px 12px", background: "rgba(239, 68, 68, 0.1)", color: "#f87171", border: "1px solid rgba(239, 68, 68, 0.2)", fontSize: "0.85rem" }}>
                  Change Image
                </button>
              </div>
            )}
          </div>

          <button className="primary-btn" disabled={loading || !file} style={{ marginTop: "12px" }}>
            {loading ? "Initializing..." : "Run AI Analysis"}
          </button>
        </form>
      </div>

      {loading && (
        <div className="card loader-wrap" style={{ marginTop: "24px", animation: "fadeUp 0.3s ease-out" }}>
          <div className="spinner-glow" />
          <div className="loading-text">{loadingMessage}</div>
        </div>
      )}

      {error ? <div className="error-box">{error}</div> : null}

      {result && !loading ? (
        <div className="result-grid">
          <div className="card" style={{ borderLeft: `4px solid ${getBarColor(result.predicted_class)}` }}>
            <h3 style={{ margin: "0 0 16px 0", color: "#ffffff" }}>Diagnostic Finding</h3>
            <p style={{ margin: "0 0 8px 0" }}><strong>Disease:</strong> {result.predicted_disease}</p>
            <p style={{ margin: "0 0 8px 0" }}>
              <strong>Result Class:</strong>{" "}
              <span style={{ color: getBarColor(result.predicted_class), fontWeight: "bold" }}>
                {result.predicted_class}
              </span>
            </p>
            <p style={{ margin: "0 0 8px 0" }}><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
            <p style={{ margin: "0 0 8px 0" }}><strong>Certainty:</strong> {result.certainty}</p>
            <p style={{ margin: "0 0 8px 0" }}><strong>Risk Level:</strong> {result.risk_level}</p>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--muted)", borderTop: "1px solid var(--border)", paddingTop: "12px", marginTop: "12px" }}>
              <strong>Note:</strong> {result.suggestion}
            </p>
          </div>

          <div className="card">
            <h3 style={{ margin: "0 0 16px 0", color: "#ffffff" }}>Analysis Breakdown</h3>
            <div style={{ display: "grid", gap: "12px", marginTop: "8px" }}>
              {Object.entries(result.probabilities).map(([className, score]) => (
                <div key={className}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "0.9rem" }}>
                    <span style={{ fontWeight: 500 }}>{className}</span>
                    <span>{(score * 100).toFixed(2)}%</span>
                  </div>
                  <div style={{ height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
                    <div
                      className="progress-bar-fill"
                      style={{
                        height: "100%",
                        width: `${score * 100}%`,
                        background: getBarColor(className),
                        borderRadius: "3px",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3 style={{ margin: "0 0 16px 0", color: "#ffffff" }}>Diagnostic Assets</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
              {result.heatmap_url ? (
                <a
                  href={result.heatmap_url.startsWith("http") ? result.heatmap_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${result.heatmap_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="primary-btn"
                  style={{ textDecoration: "none", color: "white" }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  </svg>
                  View Heatmap Analysis
                </a>
              ) : (
                <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.9rem" }}>No heatmap visual computed</p>
              )}
              
              {result.report_url ? (
                <a
                  href={result.report_url.startsWith("http") ? result.report_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${result.report_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="primary-btn"
                  style={{
                    textDecoration: "none",
                    color: "white",
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    boxShadow: "0 4px 12px rgba(16, 185, 203, 0.15)"
                  }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Download Analysis PDF
                </a>
              ) : (
                <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.9rem" }}>No report generated</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
