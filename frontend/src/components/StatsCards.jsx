import React, { useState, useEffect } from "react";
import { api } from "../api/client";

export default function StatsCards() {
  const [stats, setStats] = useState({
    total_predictions: 0,
    malaria_cases: 0,
    anemia_cases: 0,
    leukemia_cases: 0,
    lung_cases: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get("/admin/summary");
      setStats(response.data);
    } catch (err) {
      console.error("Error fetching stats:", err);
    } finally {
      setLoading(false);
    }
  };

  const items = [
    { title: "Total Predictions", value: stats.total_predictions || 0 },
    { title: "Malaria Cases", value: stats.malaria_cases || 0 },
    { title: "Anemia Cases", value: stats.anemia_cases || 0 },
    { title: "Leukemia Cases", value: stats.leukemia_cases || 0 },
    { title: "Lung X-Ray Cases", value: stats.lung_cases || 0 }
  ];

  if (loading) {
    return (
      <div className="stats-grid">
        <div className="card stat-card">
          <div className="muted">Loading stats...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="stats-grid">
      {items.map((item) => (
        <div className="card stat-card" key={item.title}>
          <div className="muted">{item.title}</div>
          <div className="stat-value">{item.value}</div>
        </div>
      ))}
    </div>
  );
}
