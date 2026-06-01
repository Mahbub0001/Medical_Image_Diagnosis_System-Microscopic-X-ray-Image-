import React, { useState, useEffect } from "react";
import { api } from "../api/client";

export default function HistoryPage() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  return (
    <div className="page">
      <div className="page-header">
        <h2>Prediction History</h2>
        <p>View previous records and review past analysis sessions.</p>
      </div>

      {loading ? (
        <div className="card">
          <p>Loading prediction history...</p>
        </div>
      ) : error ? (
        <div className="error-box">{error}</div>
      ) : predictions.length === 0 ? (
        <div className="card">
          <p>No predictions yet. Upload an image to get started!</p>
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Disease</th>
                <th>Predicted Class</th>
                <th>Confidence</th>
                <th>Certainty</th>
                <th>Risk Level</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.predicted_disease}</td>
                  <td>{item.predicted_class}</td>
                  <td>{formatConfidence(item.confidence)}</td>
                  <td>{item.certainty}</td>
                  <td>{item.risk_level}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td>
                    {item.report_url && (
                      <a
                        href={item.report_url.startsWith("http") ? item.report_url : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${item.report_url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        View Report
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
