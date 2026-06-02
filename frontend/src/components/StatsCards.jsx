import React, { useState, useEffect } from "react";
import { api } from "../api/client";

const COLORS = [
  "#8b5cf6", // Violet for Total
  "#ef4444", // Rose for Malaria (often critical)
  "#fbbf24", // Amber for Anemia
  "#a78bfa", // Light violet for Leukemia
  "#3b82f6"  // Blue for Lung X-Ray
];

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
        <div className="card stat-card" style={{ borderLeft: `3px solid ${COLORS[0]}` }}>
          <div className="muted">Loading stats...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="stats-grid">
      {items.map((item, index) => {
        const activeColor = COLORS[index % COLORS.length];
        return (
          <div 
            className="card stat-card" 
            key={item.title}
            style={{ 
              animation: "fadeUp 0.5s ease-out both",
              animationDelay: `${index * 0.08}s`,
              borderLeft: `3px solid ${activeColor}`
            }}
          >
            <div className="muted" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ 
                width: "8px", 
                height: "8px", 
                borderRadius: "50%", 
                backgroundColor: activeColor,
                boxShadow: `0 0 6px ${activeColor}`
              }} />
              {item.title}
            </div>
            <div className="stat-value">{item.value}</div>
          </div>
        );
      })}
    </div>
  );
}
