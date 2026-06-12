import React from "react";

export default function ReportsPage() {
  const templates = [
    {
      title: "Comprehensive Lab Report",
      description: "Includes microscopic cells ratio, neural certainty graphs, full clinical suggestions, and reference ranges.",
      badge: "PDF Format",
      color: "#8b5cf6"
    },
    {
      title: "Patient Summary Slip",
      description: "Quick single-page summary suitable for quick handoffs, containing risk matrix pill tags and basic recommendations.",
      badge: "Print Ready",
      color: "#10b981"
    },
    {
      title: "Neural Activation Map (Grad-CAM)",
      description: "Full resolution export of the neural network visual layers highlighting hot spots of diagnostic importance.",
      badge: "PNG/JPG Image",
      color: "#3b82f6"
    }
  ];

  return (
    <div className="page" style={{ animation: "fadeUp 0.5s ease-out" }}>
      <div className="page-header">
        <h2>Medical Report Center</h2>
        <p>Manage, generate, and export diagnosis summaries and explainable neural heatmap assets.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px", marginBottom: "32px" }}>
        {templates.map((tpl, idx) => (
          <div 
            className="card" 
            key={tpl.title}
            style={{ 
              borderTop: `4px solid ${tpl.color}`,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              animation: "fadeUp 0.5s ease-out both",
              animationDelay: `${idx * 0.1}s`
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3 style={{ margin: 0, fontSize: "1.15rem", color: "var(--heading)" }}>{tpl.title}</h3>
                <span style={{ fontSize: "0.75rem", background: "var(--badge-tag-bg)", border: "1px solid var(--border)", padding: "2px 8px", borderRadius: "9999px", color: "var(--muted)", fontWeight: "600" }}>{tpl.badge}</span>
              </div>
              <p style={{ margin: "0 0 20px 0", fontSize: "0.9rem", color: "var(--muted)", lineHeight: 1.5 }}>{tpl.description}</p>
            </div>
            
            <button 
              className="primary-btn" 
              style={{ 
                width: "100%", 
                background: "var(--badge-tag-bg)", 
                border: "1px solid var(--border)", 
                color: "var(--text)", 
                boxShadow: "none" 
              }}
              onClick={() => alert("This mockup action represents future clinical integration.")}
            >
              Configure Template
            </button>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ margin: "0 0 16px 0", color: "var(--heading)" }}>Clinical Architecture & Roadmap</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px", marginTop: "16px" }}>
          <div>
            <h4 style={{ margin: "0 0 8px 0", color: "var(--primary)" }}>📊 Diagnostic Schematics</h4>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.5 }}>
              Each report automatically fetches cell classifications, Grad-CAM overlays, patient name tags, and system certainty meters directly from the database.
            </p>
          </div>
          <div>
            <h4 style={{ margin: "0 0 8px 0", color: "#10b981" }}>💾 Supabase Database Backup</h4>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.5 }}>
              All diagnostics are permanently logged inside PostgreSQL. Media links are uploaded to Cloudinary so that reports remain accessible on demand.
            </p>
          </div>
          <div>
            <h4 style={{ margin: "0 0 8px 0", color: "#3b82f6" }}>🚀 Future Features</h4>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.5 }}>
              Upcoming phases include full client-side PDF compilation using <code>jsPDF</code> and automated email triggers to doctors upon critical alert.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
