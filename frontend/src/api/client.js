import axios from "axios";
import { Capacitor } from "@capacitor/core";

// Default API URL fallback
// If running inside native Android, we can default to empty or stored URL or env var
const DEFAULT_URL = import.meta.env.VITE_API_URL || "https://mahbub0001-medical-image-classifier.hf.space";

export const getApiBaseUrl = () => {
  const saved = localStorage.getItem("biolens_api_url");
  if (saved && saved.trim()) {
    return saved.trim().replace(/\/+$/, "");
  }
  return DEFAULT_URL.replace(/\/+$/, "");
};

export const setApiBaseUrl = (url) => {
  if (!url || !url.trim()) {
    localStorage.removeItem("biolens_api_url");
  } else {
    localStorage.setItem("biolens_api_url", url.trim().replace(/\/+$/, ""));
  }
};

export const isNativeApp = () => {
  return Capacitor.isNativePlatform();
};

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 120000, // 2 minutes for heavy ML inference
});

// Dynamically attach the active baseURL before each request
api.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl();
  config.headers["ngrok-skip-browser-warning"] = "true";

  // When uploading FormData, let browser/WebView automatically set Content-Type with correct boundary
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
    delete config.headers["content-type"];
  }
  return config;
});

// Helper to resolve static assets (heatmaps, reports, uploads) against current API server
export const resolveServerUrl = (path) => {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const base = getApiBaseUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
};
