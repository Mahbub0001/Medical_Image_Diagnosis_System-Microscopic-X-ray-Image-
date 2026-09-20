import React, { useState } from "react";
import { getApiBaseUrl, setApiBaseUrl, api } from "../api/client";

export default function ServerSettingsModal({ isOpen, onClose }) {
  const [url, setUrl] = useState(getApiBaseUrl());
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const cleanUrl = url.trim().replace(/\/+$/, "");
      const res = await fetch(`${cleanUrl}/`, {
        method: "GET",
        headers: {
          "Accept": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
      });
      if (res.ok) {
        const data = await res.json();
        setTestResult({
          success: true,
          message: `Connected! Response: "${data.message || "BioLens API online"}"`,
        });
      } else {
        setTestResult({
          success: false,
          message: `Server returned HTTP ${res.status}`,
        });
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: `Connection failed: ${err.message}. Ensure backend is running and reachable.`,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    setApiBaseUrl(url);
    onClose();
    window.location.reload(); // Refresh to re-initialize with new server URL
  };

  const handleReset = () => {
    setApiBaseUrl("");
    const defaultUrl = import.meta.env.VITE_API_URL || "https://mahbub0001-medical-image-classifier.hf.space";
    setUrl(defaultUrl);
    setTestResult(null);
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "480px",
          background: "var(--card-solid, #1e293b)",
          borderRadius: "16px",
          padding: "24px",
          boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ margin: 0, color: "var(--heading)", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>⚙️</span> Backend Server Settings
          </h3>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--muted)",
              fontSize: "1.2rem",
              cursor: "pointer",
              padding: "4px 8px",
            }}
          >
            ✕
          </button>
        </div>

        <p style={{ fontSize: "0.88rem", color: "var(--muted)", margin: "0 0 16px 0", lineHeight: "1.4" }}>
          Configure the AI Inference Backend URL. On Android phones, enter your live cloud URL (e.g. Render) or your local PC Wi-Fi IP (e.g. <code>http://192.168.1.105:10000</code>).
        </p>

        <label style={{ display: "block", marginBottom: "12px", fontSize: "0.85rem", fontWeight: 600, color: "var(--label-color)" }}>
          API Base URL:
          <input
            type="text"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setTestResult(null);
            }}
            placeholder="e.g. https://biolens-backend.onrender.com"
            style={{ marginTop: "6px", width: "100%" }}
          />
        </label>

        {testResult && (
          <div
            style={{
              padding: "10px 14px",
              borderRadius: "8px",
              marginBottom: "16px",
              fontSize: "0.85rem",
              background: testResult.success ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
              color: testResult.success ? "var(--success)" : "var(--danger)",
              border: `1px solid ${testResult.success ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            }}
          >
            {testResult.message}
          </div>
        )}

        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", flexWrap: "wrap", marginTop: "20px" }}>
          <button
            type="button"
            onClick={handleReset}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              color: "var(--muted)",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            Reset Default
          </button>
          <button
            type="button"
            onClick={handleTest}
            disabled={testing}
            style={{
              padding: "10px 16px",
              background: "var(--hover-bg)",
              border: "1px solid var(--primary)",
              borderRadius: "10px",
              color: "var(--primary)",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: 600,
            }}
          >
            {testing ? "Testing..." : "Test Connection"}
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={handleSave}
            style={{ padding: "10px 18px", fontSize: "0.85rem" }}
          >
            Save &amp; Apply
          </button>
        </div>
      </div>
    </div>
  );
}
