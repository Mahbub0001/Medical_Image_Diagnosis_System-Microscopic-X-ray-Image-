import React, { Suspense, lazy } from "react";
import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";

// Lazy load pages to split the application bundle
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UploadPage = lazy(() => import("./pages/UploadPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));

export default function App() {
  return (
    <AppLayout>
      <Suspense fallback={
        <div className="page" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "15px" }}>
            <div className="spinner-glow"></div>
            <div className="loading-text">Loading page...</div>
          </div>
        </div>
      }>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </Suspense>
    </AppLayout>
  );
}
