import React, { useState, useEffect } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api/client";

const COLORS = ["#22c55e", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"];

export default function PredictionSummaryChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChartData();
  }, []);

  const fetchChartData = async () => {
    try {
      const response = await api.get("/admin/summary");
      const summary = response.data;
      
      // Build chart data from disease breakdown
      const chartData = [];
      if (summary.disease_breakdown) {
        Object.entries(summary.disease_breakdown).forEach(([disease, count]) => {
          chartData.push({ name: disease, value: count });
        });
      }
      
      setData(chartData.length > 0 ? chartData : [
        { name: "Malaria", value: 0 },
        { name: "Anemia", value: 0 },
        { name: "Leukemia", value: 0 }
      ]);
    } catch (err) {
      console.error("Error fetching chart data:", err);
      setData([
        { name: "Malaria", value: 0 },
        { name: "Anemia", value: 0 },
        { name: "Leukemia", value: 0 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card chart-card">
        <h3>Prediction Summary</h3>
        <p>Loading chart data...</p>
      </div>
    );
  }

  if (data.length === 0 || data.every(d => d.value === 0)) {
    return (
      <div className="card chart-card">
        <h3>Prediction Summary</h3>
        <p>No predictions yet. Upload images to see the summary!</p>
      </div>
    );
  }

  return (
    <div className="card chart-card">
      <h3>Prediction Summary</h3>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={90} label>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
