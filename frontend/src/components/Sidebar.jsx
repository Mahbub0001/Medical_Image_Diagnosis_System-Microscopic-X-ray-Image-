import React, { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";

const links = [
  { 
    to: "/", 
    label: "Dashboard",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="9" />
        <rect x="14" y="3" width="7" height="5" />
        <rect x="14" y="12" width="7" height="9" />
        <rect x="3" y="16" width="7" height="5" />
      </svg>
    )
  },
  { 
    to: "/upload", 
    label: "Blood Smear",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22a7 7 0 0 0 7-7c0-4.3-7-13-7-13S5 10.7 5 15a7 7 0 0 0 7 7z" />
      </svg>
    )
  },
  { 
    to: "/lung-xray", 
    label: "Lung X-Ray",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 20a6 6 0 0 1-6-6c0-3.3 2-7 6-10v16z" />
        <path d="M15 20a6 6 0 0 0 6-6c0-3.3-2-7-6-10v16z" />
        <path d="M12 4v6" />
      </svg>
    )
  },
  { 
    to: "/history", 
    label: "History",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 8v4l3 3" />
        <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5" />
      </svg>
    )
  },
  { 
    to: "/reports", 
    label: "Reports",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    )
  }
];

const themes = [
  { id: "midnight", color: "#8b5cf6", name: "Midnight Neon" },
  { id: "emerald", color: "#10b981", name: "Emerald Green" },
  { id: "nordic", color: "#0284c7", name: "Nordic Frost" },
  { id: "sunset", color: "#f97316", name: "Sunset Glow" }
];

export default function Sidebar() {
  const [activeTheme, setActiveTheme] = useState(() => {
    return localStorage.getItem("app-theme") || "midnight";
  });

  useEffect(() => {
    themes.forEach((t) => {
      document.documentElement.classList.remove(`theme-${t.id}`);
    });
    document.documentElement.classList.add(`theme-${activeTheme}`);
    localStorage.setItem("app-theme", activeTheme);
  }, [activeTheme]);

  return (
    <aside className="sidebar">
      <div className="brand-card">
        <h1>BloodDetect AI</h1>
        <p>Smart Medical Analysis</p>
      </div>
      <nav className="sidebar-nav">
        {links.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="theme-switcher-container">
        <span className="theme-label">Theme</span>
        <div className="theme-buttons">
          {themes.map((t) => (
            <button
              key={t.id}
              className={`theme-btn ${activeTheme === t.id ? "active" : ""}`}
              style={{ backgroundColor: t.color }}
              title={t.name}
              onClick={() => setActiveTheme(t.id)}
              aria-label={`Switch to ${t.name}`}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
