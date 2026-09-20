import React, { useState, useEffect, useCallback } from "react";
import { api, resolveServerUrl } from "../api/client";
import { compressImage } from "../utils/imageCompressor";

// ── constants ────────────────────────────────────────────────────────────────
const TESTS = [
  {
    key: "anemia",
    label: "Anemia",
    emoji: "🩸",
    desc: "RBC morphology analysis",
    accent: "#ef4444",
    fieldName: "anemia_image",
  },
  {
    key: "malaria",
    label: "Malaria",
    emoji: "🦠",
    desc: "Parasite detection",
    accent: "#f59e0b",
    fieldName: "malaria_image",
  },
  {
    key: "leukemia",
    label: "Leukemia",
    emoji: "🔬",
    desc: "WBC blast cell analysis",
    accent: "#8b5cf6",
    fieldName: "leukemia_image",
  },
];

const LOADING_MESSAGES_SINGLE = [
  "Uploading microscopic smear to pipeline...",
  "Validating cell aspect ratios and colors...",
  "Evaluating structures via Blood Ensemble Model...",
  "Performing automatic multi-disease classification...",
  "Synthesizing Grad-CAM explainability map...",
  "Generating final medical PDF report...",
];

const LOADING_MESSAGES_COMP = [
  "Uploading blood smear images...",
  "Running Blood Ensemble Model on each slide...",
  "Generating Grad-CAM heatmaps...",
  "Compiling comprehensive hematology findings...",
  "Building combined diagnostic PDF report...",
  "Finalising your Comprehensive Blood Panel...",
];

// ── helpers ──────────────────────────────────────────────────────────────────
const formatFileSize = (bytes) => {
  if (!bytes) return "";
  const kb = bytes / 1024;
  return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(1)} MB`;
};

const getBarColor = (className = "") => {
  const c = className.toLowerCase();
  if (c.includes("normal") || c.includes("uninfected") || c.includes("benign"))
    return "var(--success)";
  if (
    c.includes("parasitized") ||
    c.includes("anemic") ||
    c.includes("pro") ||
    c.includes("early")
  )
    return "var(--danger)";
  return "var(--warning)";
};

const getRiskColor = (risk = "") => {
  if (risk.includes("High")) return "var(--danger)";
  if (risk.includes("Moderate")) return "var(--warning)";
  if (risk.includes("Review")) return "#60a5fa";
  return "var(--success)";
};

// ── SlotUploader sub-component ───────────────────────────────────────────────
function SlotUploader({ test, slotState, onFileSet, onClear }) {
  const { file, previewUrl, compressing, compressionInfo } = slotState;
  const [dragActive, setDragActive] = useState(false);
  const inputId = `file-select-${test.key}`;

  const processFile = useCallback(
    async (selectedFile) => {
      const preview = URL.createObjectURL(selectedFile);
      onFileSet(test.key, { file: selectedFile, previewUrl: preview, compressing: false, compressionInfo: null, compressedFile: null });

      if (selectedFile.size > 200 * 1024) {
        onFileSet(test.key, (prev) => ({ ...prev, compressing: true }));
        try {
          const compressed = await compressImage(selectedFile);
          onFileSet(test.key, (prev) => ({
            ...prev,
            compressing: false,
            compressedFile: compressed,
            compressionInfo: { originalSize: selectedFile.size, compressedSize: compressed.size },
          }));
        } catch {
          onFileSet(test.key, (prev) => ({ ...prev, compressing: false }));
        }
      }
    },
    [test.key, onFileSet]
  );

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) processFile(f);
  };

  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (f) processFile(f);
  };

  return (
    <div className="slot-card" style={{ "--slot-accent": test.accent }}>
      <div className="slot-header">
        <span className="slot-emoji">{test.emoji}</span>
        <div>
          <p className="slot-title">{test.label} Screening</p>
          <p className="slot-desc">{test.desc}</p>
        </div>
      </div>

      {!file ? (
        <div
          className={`drop-zone drop-zone--compact ${dragActive ? "dragover" : ""}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => document.getElementById(inputId).click()}
          style={{ "--dz-accent": test.accent }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <p className="dz-label">Drop image or <span style={{ color: test.accent }}>browse</span></p>
          <input
            id={inputId}
            type="file"
            accept=".jpg,.jpeg,.png"
            onChange={handleChange}
            style={{ display: "none" }}
          />
        </div>
      ) : (
        <div className="slot-preview">
          <img src={previewUrl} alt="Preview" className="slot-thumb" />
          <div className="slot-meta">
            <p className="slot-filename">{file.name}</p>
            {compressing ? (
              <p className="slot-status compressing">⚙️ Compressing…</p>
            ) : compressionInfo ? (
              <p className="slot-status compressed">
                ✅ {formatFileSize(compressionInfo.originalSize)} → {formatFileSize(compressionInfo.compressedSize)}
                {" "}({Math.round((1 - compressionInfo.compressedSize / compressionInfo.originalSize) * 100)}% smaller)
              </p>
            ) : (
              <p className="slot-status">{formatFileSize(file.size)}</p>
            )}
          </div>
          <button
            type="button"
            className="slot-clear-btn"
            onClick={() => onClear(test.key)}
            title="Remove image"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

// ── FindingPanel sub-component (comprehensive results) ────────────────────────
function FindingPanel({ finding, index }) {
  const [open, setOpen] = useState(true);
  const accentMap = { Anemia: "#ef4444", Malaria: "#f59e0b", Leukemia: "#8b5cf6" };
  const accent = accentMap[finding.test_label] || "var(--primary)";

  return (
    <div className="finding-panel" style={{ "--fp-accent": accent }}>
      <button
        className="finding-panel__header"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="finding-panel__label">
          Panel {index + 1}: {finding.test_label} Screening
        </span>
        <span
          className="finding-panel__badge"
          style={{
            background: `${getBarColor(finding.predicted_class)}22`,
            color: getBarColor(finding.predicted_class),
            border: `1px solid ${getBarColor(finding.predicted_class)}44`,
          }}
        >
          {finding.predicted_class}
        </span>
        <svg
          className={`finding-panel__chevron ${open ? "open" : ""}`}
          xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="finding-panel__body">
          <div className="finding-meta-grid">
            <div className="finding-meta-item">
              <span className="fmi-label">Disease</span>
              <span className="fmi-value">{finding.predicted_disease}</span>
            </div>
            <div className="finding-meta-item">
              <span className="fmi-label">Confidence</span>
              <span className="fmi-value">{(finding.confidence * 100).toFixed(2)}%</span>
            </div>
            <div className="finding-meta-item">
              <span className="fmi-label">Certainty</span>
              <span className="fmi-value">{finding.certainty}</span>
            </div>
            <div className="finding-meta-item">
              <span className="fmi-label">Risk Level</span>
              <span className="fmi-value" style={{ color: getRiskColor(finding.risk_level), fontWeight: 700 }}>
                {finding.risk_level}
              </span>
            </div>
          </div>

          {finding.probabilities && Object.keys(finding.probabilities).length > 0 && (
            <div className="prob-breakdown">
              {Object.entries(finding.probabilities).map(([cls, score]) => (
                <div key={cls} className="prob-row">
                  <span className="prob-label">{cls}</span>
                  <div className="prob-bar-wrap">
                    <div
                      className="prob-bar-fill"
                      style={{ width: `${score * 100}%`, background: getBarColor(cls) }}
                    />
                  </div>
                  <span className="prob-pct">{(score * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}

          {finding.heatmap_url && (
            <div style={{ marginTop: "14px", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--border)", background: "#0f172a" }}>
              <img
                src={resolveServerUrl(finding.heatmap_url)}
                alt={`${finding.test_label} Grad-CAM Heatmap`}
                style={{ width: "100%", height: "auto", display: "block", objectFit: "contain" }}
              />
            </div>
          )}

          {finding.suggestion && (
            <p className="finding-suggestion">{finding.suggestion}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Page Component ───────────────────────────────────────────────────────
export default function UploadPage() {
  // ── Shared state ──────────────────────────────────────────────────────────
  const [mode, setMode] = useState("single"); // "single" | "comprehensive"
  const [patientName, setPatientName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Processing...");
  const [error, setError] = useState("");

  // ── Single-test state ─────────────────────────────────────────────────────
  const [file, setFile] = useState(null);
  const [compressedFile, setCompressedFile] = useState(null);
  const [compressionInfo, setCompressionInfo] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [compressing, setCompressing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [singleResult, setSingleResult] = useState(null);

  // ── Comprehensive-panel state ─────────────────────────────────────────────
  const [selectedTests, setSelectedTests] = useState(new Set(["anemia"]));
  const initialSlot = { file: null, previewUrl: "", compressing: false, compressionInfo: null, compressedFile: null };
  const [slots, setSlots] = useState({ anemia: { ...initialSlot }, malaria: { ...initialSlot }, leukemia: { ...initialSlot } });
  const [compResult, setCompResult] = useState(null);

  // ── Loading message rotator ───────────────────────────────────────────────
  useEffect(() => {
    let interval;
    if (loading) {
      const messages = mode === "comprehensive" ? LOADING_MESSAGES_COMP : LOADING_MESSAGES_SINGLE;
      let i = 0;
      setLoadingMessage(messages[0]);
      interval = setInterval(() => {
        i = (i + 1) % messages.length;
        setLoadingMessage(messages[i]);
      }, 1400);
    }
    return () => clearInterval(interval);
  }, [loading, mode]);

  // ── Single-test helpers ───────────────────────────────────────────────────
  const processSingleFile = async (selectedFile) => {
    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
    setCompressionInfo(null);
    setCompressedFile(null);
    if (selectedFile.size > 200 * 1024) {
      setCompressing(true);
      try {
        const compressed = await compressImage(selectedFile);
        setCompressedFile(compressed);
        setCompressionInfo({ originalSize: selectedFile.size, compressedSize: compressed.size });
      } catch { setCompressedFile(null); }
      finally { setCompressing(false); }
    }
  };

  const handleSingleDrag = (e) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };
  const handleSingleDrop = (e) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) processSingleFile(e.dataTransfer.files[0]);
  };
  const clearSingle = () => { setFile(null); setCompressedFile(null); setCompressionInfo(null); setPreviewUrl(""); setSingleResult(null); setError(""); };

  // ── Comprehensive helpers ─────────────────────────────────────────────────
  const toggleTest = (key) => {
    setSelectedTests((prev) => {
      const next = new Set(prev);
      if (next.has(key)) { if (next.size > 1) next.delete(key); }
      else next.add(key);
      return next;
    });
  };

  const setSlotFile = useCallback((key, updater) => {
    setSlots((prev) => ({
      ...prev,
      [key]: typeof updater === "function" ? updater(prev[key]) : updater,
    }));
  }, []);

  const clearSlot = useCallback((key) => {
    setSlots((prev) => ({ ...prev, [key]: { ...initialSlot } }));
  }, []);

  // ── Submit handlers ───────────────────────────────────────────────────────
  const onSubmitSingle = async (e) => {
    e.preventDefault();
    if (!file) return;

    if (phoneNumber && phoneNumber.trim()) {
      const cleanPhone = phoneNumber.trim();
      if (!/^01\d{9}$/.test(cleanPhone)) {
        setError("Invalid phone number! It must start with '01' and be exactly 11 digits (e.g. 01712345678).");
        return;
      }
    }

    setLoading(true); setError(""); setSingleResult(null);
    try {
      const uploadFile = compressedFile || file;
      const fd = new FormData();
      fd.append("file", uploadFile, uploadFile.name || "image.jpg");
      fd.append("patient_name", patientName || "User");
      fd.append("phone_number", phoneNumber || "");
      fd.append("disease_key", "blood");
      const res = await api.post("/predict/analyze", fd);
      setSingleResult(res.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      let msg = "Prediction failed.";
      if (typeof detail === "string") msg = detail;
      else if (detail?.error || detail?.message) msg = detail.error || detail.message;
      else if (err?.message) msg = err.message;
      setError(msg);
    } finally { setLoading(false); }
  };

  const onSubmitComprehensive = async (e) => {
    e.preventDefault();

    if (phoneNumber && phoneNumber.trim()) {
      const cleanPhone = phoneNumber.trim();
      if (!/^01\d{9}$/.test(cleanPhone)) {
        setError("Invalid phone number! It must start with '01' and be exactly 11 digits (e.g. 01712345678).");
        return;
      }
    }

    const activeTests = TESTS.filter((t) => selectedTests.has(t.key));
    const missingFiles = activeTests.filter((t) => !slots[t.key].file);
    if (missingFiles.length > 0) {
      setError(`Please upload an image for: ${missingFiles.map((t) => t.label).join(", ")}`);
      return;
    }
    setLoading(true); setError(""); setCompResult(null);
    try {
      const fd = new FormData();
      fd.append("patient_name", patientName || "User");
      fd.append("phone_number", phoneNumber || "");
      activeTests.forEach((t) => {
        const slotData = slots[t.key];
        const uploadFile = slotData.compressedFile || slotData.file;
        fd.append(t.fieldName, uploadFile, uploadFile.name || "image.jpg");
      });
      const res = await api.post("/predict/analyze-comprehensive", fd);
      setCompResult(res.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      let msg = "Analysis failed.";
      if (typeof detail === "string") msg = detail;
      else if (detail?.error || detail?.message) msg = detail.error || detail.message;
      else if (err?.message) msg = err.message;
      setError(msg);
    } finally { setLoading(false); }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  const anySlotCompressing = TESTS.some((t) => selectedTests.has(t.key) && slots[t.key].compressing);
  const selectedTestsArray = TESTS.filter((t) => selectedTests.has(t.key));
  const allSlotsReady = selectedTestsArray.every((t) => !!slots[t.key].file);

  const resolveUrl = (url) => resolveServerUrl(url);

  return (
    <div className="page">
      <div className="page-header">
        <h2>Blood Smear Classifier</h2>
        <p>Upload microscopic blood smear images to detect Malaria, Anemia, or Leukemia abnormalities.</p>
      </div>

      {/* ── Mode Toggle ─────────────────────────────────────────────────── */}
      <div className="mode-toggle" role="group" aria-label="Analysis mode">
        <button
          id="mode-single"
          className={`mode-toggle__btn ${mode === "single" ? "active" : ""}`}
          onClick={() => { setMode("single"); setError(""); setSingleResult(null); setCompResult(null); }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z" />
          </svg>
          Single Test
        </button>
        <button
          id="mode-comprehensive"
          className={`mode-toggle__btn ${mode === "comprehensive" ? "active" : ""}`}
          onClick={() => { setMode("comprehensive"); setError(""); setSingleResult(null); setCompResult(null); }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
          </svg>
          Comprehensive Panel
        </button>
      </div>

      {/* ── Patient Info (shared) ────────────────────────────────────────── */}
      <div className="card" style={{ marginTop: "20px" }}>
        <form onSubmit={mode === "single" ? onSubmitSingle : onSubmitComprehensive} className="upload-form">

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            <label>
              Patient Name
              <input value={patientName} onChange={(e) => setPatientName(e.target.value)} placeholder="Enter patient name" />
            </label>
            <label>
              Phone Number (11 Digits, starts with 01)
              <input
                type="tel"
                value={phoneNumber}
                maxLength={11}
                onChange={(e) => {
                  const digitsOnly = e.target.value.replace(/\D/g, "").slice(0, 11);
                  setPhoneNumber(digitsOnly);
                  if (error && error.includes("phone number")) setError("");
                }}
                placeholder="01XXXXXXXXX"
              />
            </label>
          </div>

          {/* ── SINGLE TEST MODE ──────────────────────────────────────────── */}
          {mode === "single" && (
            <div style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--label-color)" }}>Slide Smear Image</span>
              {!file ? (
                <div
                  className={`drop-zone ${dragActive ? "dragover" : ""}`}
                  onDragEnter={handleSingleDrag}
                  onDragOver={handleSingleDrag}
                  onDragLeave={handleSingleDrag}
                  onDrop={handleSingleDrop}
                  onClick={() => document.getElementById("file-select-single").click()}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                  </svg>
                  <div>
                    <p style={{ margin: "0 0 4px 0", fontWeight: 700, color: "var(--heading)" }}>Drag &amp; drop sample image here</p>
                    <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)" }}>or click to browse (JPG, PNG)</p>
                  </div>
                  <input id="file-select-single" type="file" accept=".jpg,.jpeg,.png" onChange={(e) => { const f = e.target.files?.[0]; if (f) processSingleFile(f); }} style={{ display: "none" }} />
                </div>
              ) : (
                <div className="card" style={{ background: "var(--hover-bg)", padding: "16px", display: "flex", alignItems: "center", gap: "16px", border: "1px dashed var(--border)" }}>
                  {previewUrl && <img src={previewUrl} alt="Preview" style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "10px", border: "1px solid var(--border)" }} />}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ margin: "0 0 4px 0", fontWeight: 600, color: "var(--heading)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</p>
                    {compressing ? (
                      <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--accent)" }}>⚙️ Compressing image...</p>
                    ) : compressionInfo ? (
                      <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--success)" }}>
                        ✅ {formatFileSize(compressionInfo.originalSize)} → {formatFileSize(compressionInfo.compressedSize)}{" "}
                        ({Math.round((1 - compressionInfo.compressedSize / compressionInfo.originalSize) * 100)}% smaller)
                      </p>
                    ) : (
                      <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--muted)" }}>Size: {formatFileSize(file.size)}</p>
                    )}
                  </div>
                  <button type="button" className="primary-btn" onClick={clearSingle} style={{ padding: "8px 12px", background: "rgba(239,68,68,0.1)", color: "var(--danger)", border: "1px solid rgba(239,68,68,0.2)", fontSize: "0.85rem" }}>
                    Change
                  </button>
                </div>
              )}
              <button className="primary-btn" disabled={loading || compressing || !file} style={{ marginTop: "4px" }}>
                {compressing ? "Compressing…" : loading ? "Analysing…" : "Run AI Analysis"}
              </button>
            </div>
          )}

          {/* ── COMPREHENSIVE PANEL MODE ──────────────────────────────────── */}
          {mode === "comprehensive" && (
            <div style={{ display: "grid", gap: "20px" }}>

              {/* Test selection chips */}
              <div>
                <span className="upload-form-label">Select Tests to Conduct</span>
                <p style={{ margin: "4px 0 12px", fontSize: "0.85rem", color: "var(--muted)" }}>
                  Select one or more diseases to screen for. Upload one smear image per selected test.
                </p>
                <div className="test-chips">
                  {TESTS.map((t) => (
                    <button
                      key={t.key}
                      id={`chip-${t.key}`}
                      type="button"
                      className={`test-chip ${selectedTests.has(t.key) ? "active" : ""}`}
                      style={{ "--chip-accent": t.accent }}
                      onClick={() => toggleTest(t.key)}
                    >
                      <span className="test-chip__check">
                        {selectedTests.has(t.key) ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                          </svg>
                        ) : null}
                      </span>
                      <span className="test-chip__emoji">{t.emoji}</span>
                      <div className="test-chip__text">
                        <span className="test-chip__name">{t.label}</span>
                        <span className="test-chip__desc">{t.desc}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Upload slots — one per selected test */}
              <div>
                <span className="upload-form-label">
                  Upload Smear Images
                  <span className="upload-form-sublabel">— {selectedTests.size} test{selectedTests.size > 1 ? "s" : ""} selected</span>
                </span>
                <div className="test-slots-grid" style={{ "--slot-count": selectedTests.size }}>
                  {TESTS.filter((t) => selectedTests.has(t.key)).map((t) => (
                    <SlotUploader
                      key={t.key}
                      test={t}
                      slotState={slots[t.key]}
                      onFileSet={setSlotFile}
                      onClear={clearSlot}
                    />
                  ))}
                </div>
              </div>

              <button
                className="primary-btn"
                disabled={loading || anySlotCompressing || !allSlotsReady}
                style={{ marginTop: "4px" }}
              >
                {anySlotCompressing
                  ? "Compressing images…"
                  : loading
                  ? "Running Comprehensive Analysis…"
                  : `Submit ${selectedTests.size} Test${selectedTests.size > 1 ? "s" : ""} for Analysis`}
              </button>
            </div>
          )}
        </form>
      </div>

      {/* ── Loading state ─────────────────────────────────────────────────── */}
      {loading && (
        <div className="card loader-wrap" style={{ marginTop: "24px", animation: "fadeUp 0.3s ease-out" }}>
          <div className="spinner-glow" />
          <div className="loading-text">{loadingMessage}</div>
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────────────────────── */}
      {error && <div className="error-box">{error}</div>}

      {/* ── Single Test Result ────────────────────────────────────────────── */}
      {singleResult && !loading && (
        <div className="result-grid">
          <div className="card" style={{ borderLeft: `4px solid ${getBarColor(singleResult.predicted_class)}` }}>
            <h3 style={{ margin: "0 0 16px 0", color: "var(--heading)" }}>Diagnostic Finding</h3>
            <p style={{ margin: "0 0 8px 0" }}><strong>Disease:</strong> {singleResult.predicted_disease}</p>
            <p style={{ margin: "0 0 8px 0" }}>
              <strong>Result Class:</strong>{" "}
              <span style={{ color: getBarColor(singleResult.predicted_class), fontWeight: "bold" }}>
                {singleResult.predicted_class}
              </span>
            </p>
            <p style={{ margin: "0 0 8px 0" }}><strong>Confidence:</strong> {(singleResult.confidence * 100).toFixed(2)}%</p>
            <p style={{ margin: "0 0 8px 0" }}><strong>Certainty:</strong> {singleResult.certainty}</p>
            <p style={{ margin: "0 0 8px 0" }}><strong>Risk Level:</strong> {singleResult.risk_level}</p>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--muted)", borderTop: "1px solid var(--border)", paddingTop: "12px", marginTop: "12px" }}>
              <strong>Note:</strong> {singleResult.suggestion}
            </p>
          </div>

          <div className="card">
            <h3 style={{ margin: "0 0 16px 0", color: "var(--heading)" }}>Analysis Breakdown</h3>
            <div style={{ display: "grid", gap: "12px", marginTop: "8px" }}>
              {Object.entries(singleResult.probabilities).map(([cls, score]) => (
                <div key={cls}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "0.9rem" }}>
                    <span style={{ fontWeight: 500 }}>{cls}</span>
                    <span>{(score * 100).toFixed(2)}%</span>
                  </div>
                  <div style={{ height: "6px", background: "var(--border)", borderRadius: "3px", overflow: "hidden" }}>
                    <div className="progress-bar-fill" style={{ height: "100%", width: `${score * 100}%`, background: getBarColor(cls), borderRadius: "3px" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3 style={{ margin: "0 0 14px 0", color: "var(--heading)" }}>Explainable AI (Grad-CAM)</h3>
            {singleResult.heatmap_url ? (
              <div style={{ marginBottom: "16px" }}>
                <div style={{ borderRadius: "8px", overflow: "hidden", border: "1px solid var(--border)", background: "#0f172a" }}>
                  <img
                    src={resolveUrl(singleResult.heatmap_url)}
                    alt="Grad-CAM Activation Heatmap"
                    style={{ width: "100%", height: "auto", display: "block", objectFit: "contain" }}
                  />
                </div>
                <p style={{ margin: "6px 0 0 0", fontSize: "0.8rem", color: "var(--muted)", textAlign: "center", fontWeight: 500 }}>
                  Input Smear &nbsp;|&nbsp; Activation &nbsp;|&nbsp; Overlay
                </p>
              </div>
            ) : (
              <p style={{ margin: "0 0 16px 0", color: "var(--muted)", fontSize: "0.9rem" }}>No heatmap visual computed</p>
            )}

            {singleResult.report_url ? (
              <a
                href={resolveUrl(singleResult.report_url)}
                target="_blank"
                rel="noopener noreferrer"
                className="primary-btn"
                style={{
                  textDecoration: "none",
                  color: "white",
                  background: "linear-gradient(135deg, #10b981, #059669)",
                  boxShadow: "0 4px 12px rgba(16,185,129,0.2)",
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  padding: "10px 16px"
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
      )}

      {/* ── Comprehensive Panel Result ──────────────────────────────────────── */}
      {compResult && !loading && (
        <div style={{ marginTop: "28px", animation: "fadeUp 0.4s ease-out" }}>

          {/* Summary banner */}
          <div className="comp-summary-banner">
            <div className="csb-stat">
              <span className="csb-stat__num">{compResult.tests_run}</span>
              <span className="csb-stat__label">Tests Conducted</span>
            </div>
            <div className="csb-divider" />
            <div className="csb-stat">
              <span className="csb-stat__num" style={{ color: "var(--danger)" }}>
                {compResult.findings.filter((f) => !["Normal", "Uninfected", "Benign"].includes(f.predicted_class)).length}
              </span>
              <span className="csb-stat__label">Positive Findings</span>
            </div>
            <div className="csb-divider" />
            <div className="csb-stat">
              <span
                className="csb-stat__num"
                style={{
                  color: getRiskColor(
                    compResult.findings.reduce((worst, f) => {
                      const priority = { "High Risk": 3, "Moderate Risk": 2, "Review Needed": 1, "Low Risk": 0 };
                      return (priority[f.risk_level] || 0) > (priority[worst] || 0) ? f.risk_level : worst;
                    }, "Low Risk")
                  ),
                }}
              >
                {compResult.findings.reduce((worst, f) => {
                  const priority = { "High Risk": 3, "Moderate Risk": 2, "Review Needed": 1, "Low Risk": 0 };
                  return (priority[f.risk_level] || 0) > (priority[worst] || 0) ? f.risk_level : worst;
                }, "Low Risk")}
              </span>
              <span className="csb-stat__label">Overall Risk</span>
            </div>
            <div className="csb-divider" />
            <div className="csb-download">
              {compResult.report_url && (
                <a
                  href={resolveUrl(compResult.report_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="primary-btn"
                  style={{ textDecoration: "none", color: "white", background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 4px 12px rgba(16,185,129,0.25)", whiteSpace: "nowrap" }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Download Combined Report
                </a>
              )}
            </div>
          </div>

          {/* Per-disease finding panels */}
          <div style={{ display: "grid", gap: "12px", marginTop: "16px" }}>
            {compResult.findings.map((finding, i) => (
              <FindingPanel key={i} finding={finding} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
