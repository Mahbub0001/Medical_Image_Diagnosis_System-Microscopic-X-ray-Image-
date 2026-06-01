import React, { useState, useEffect } from "react";
import StatsCards from "../components/StatsCards";
import PredictionSummaryChart from "../components/PredictionSummaryChart";
import { api } from "../api/client";

export default function DashboardPage() {
  const [recentPrediction, setRecentPrediction] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentPrediction();
  }, []);

  const fetchRecentPrediction = async () => {
    try {
      const response = await api.get("/predict/history");
      const predictions = response.data;
      if (predictions && predictions.length > 0) {
        setRecentPrediction(predictions[0]); // Most recent (first in the list)
      }
    } catch (err) {
      console.error("Error fetching recent prediction:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatConfidence = (confidence) => {
    if (confidence === undefined || confidence === null) return "N/A";
    return `${(confidence * 100).toFixed(2)}%`;
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Welcome back. Review prediction activity and overall system health.</p>
      </div>

      <StatsCards />

      <div className="dashboard-grid">
        <div className="card">
          <h3>Recent Prediction</h3>
          {loading ? (
            <p>Loading...</p>
          ) : recentPrediction ? (
            <>
              <p><strong>Disease:</strong> {recentPrediction.predicted_disease}</p>
              <p><strong>Class:</strong> {recentPrediction.predicted_class}</p>
              <p><strong>Confidence:</strong> {formatConfidence(recentPrediction.confidence)}</p>
              <p><strong>Certainty:</strong> {recentPrediction.certainty}</p>
              <p><strong>Risk Level:</strong> {recentPrediction.risk_level}</p>
              <p><strong>Date:</strong> {new Date(recentPrediction.created_at).toLocaleString()}</p>
            </>
          ) : (
            <p>No predictions yet. Upload an image to get started!</p>
          )}
        </div>

        <PredictionSummaryChart />

        <div className="card">
          <h3>Disease Information</h3>
          <ul>
            <li><strong>Malaria:</strong> mosquito-borne disease caused by Plasmodium parasites.</li>
            <li><strong>Anemia:</strong> reduced healthy red blood cells or hemoglobin.</li>
            <li><strong>Leukemia:</strong> blood cancer affecting white blood cells.</li>
            <li><strong>Lung X-Ray:</strong> detects Pneumonia, Tuberculosis, or Normal lungs from chest X-ray images.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
