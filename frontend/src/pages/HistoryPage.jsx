import React, { useState, useEffect } from "react";
import { api } from "../api/client";

export default function HistoryPage() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchPredictions();
  }, []);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      const response = await api.get("/predict/history");
      setPredictions(response.data);
      setError("");
    } catch (err) {
      setError("Failed to load prediction history");
      console.error("Error fetching predictions:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatConfidence = (confidence) => {
    if (confidence === undefined || confidence === null) return "N/A";
    return `${(confidence * 100).toFixed(2)}%`;
  };

  const getRiskBadgeClass = (riskLevel) => {
    const r = (riskLevel || "").toLowerCase();
    if (r.includes("low")) return "status-badge low";
    if (r.includes("mod")) return "status-badge moderate";
    if (r.includes("high")) return "status-badge high";
    return "status-badge review";
  };

  const filteredPredictions = predictions.filter((item) => {
    const query = searchQuery.toLowerCase();
    const patientName = (item.notes || "").replace("Patient: ", "").toLowerCase();
    const diseaseName = (item.predicted_disease || "").toLowerCase();
    const className = (item.predicted_class || "").toLowerCase();
    return (
      patientName.includes(query) ||
      diseaseName.includes(query) ||
      className.includes(query)
    );
  });

  return (
    <div className="page">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "16px", marginBottom: "24px" }}>
        <div>
          <h2>Prediction History</h2>
          <p>Review past analysis sessions, patient reports, and neural network evaluations.</p>
        </div>
        
        <div style={{ minWidth: "280px" }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 Search by patient, disease, or finding..."
            style={{ width: "100%", background: "var(--input-bg)" }}
          />
        </div>
      </div>

      {loading ? (
        <div className="card loader-wrap">
          <div className="spinner-glow" />
          <div className="loading-text">Loading archives...</div>
        </div>
      ) : error ? (
        <div className="error-box">{error}</div>
      ) : predictions.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px" }}>
          <p style={{ margin: "0 0 16px 0", color: "var(--muted)" }}>No predictions recorded yet.</p>
          <a href="/upload" className="primary-btn" style={{ textDecoration: "none", color: "white" }}>
            Upload First Sample
          </a>
        </div>
      ) : filteredPredictions.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px" }}>
          <p style={{ margin: 0, color: "var(--muted)" }}>No matching history records found for "{searchQuery}".</p>
        </div>
      ) : (
        <div className="card" style={{ overflowX: "auto", padding: "0" }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ paddingLeft: "24px" }}>Patient Name</th>
                <th>Diagnostic Type</th>
                <th>Result Classification</th>
                <th>Confidence</th>
                <th>Certainty</th>
                <th>Risk Matrix</th>
                <th>Timestamp</th>
                <th style={{ paddingRight: "24px" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredPredictions.map((item, index) => {
                // Extract patient name from notes if formatted as "Patient: Alice"
                const patientDisplay = (item.notes || "").replace("Patient: ", "");
                return (
                  <tr key={item.id} style={{ animation: "fadeUp 0.3s ease-out both", animationDelay: `${index * 0.04}s` }}>
                    <td style={{ paddingLeft: "24px", fontWeight: "600", color: "var(--heading)" }}>
                      {patientDisplay || "Default"}
                    </td>
                    <td>{item.predicted_disease}</td>
                    <td style={{ fontWeight: "500" }}>{item.predicted_class}</td>
                    <td>{formatConfidence(item.confidence)}</td>
                    <td>{item.certainty}</td>
                    <td>
                      <span className={getRiskBadgeClass(item.risk_level)}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                      {formatDate(item.created_at)}
                    </td>
                    <td style={{ paddingRight: "24px" }}>
                      {item.report_url ? (
                        <a
                          href={item.report_url.startsWith("http") ? item.report_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${item.report_url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="primary-btn"
                          style={{
                            padding: "6px 12px",
                            fontSize: "0.8rem",
                            background: "rgba(139, 92, 246, 0.1)",
                            color: "var(--primary)",
                            border: "1px solid rgba(139, 92, 246, 0.2)",
                            boxShadow: "none"
                          }}
                        >
                          View Report
                        </a>
                      ) : (
                        <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>N/A</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
