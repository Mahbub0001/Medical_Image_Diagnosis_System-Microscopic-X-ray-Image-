import React from "react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/upload", label: "Upload Image" },
  { to: "/lung-xray", label: "Lung X-Ray" },
  { to: "/history", label: "Prediction History" },
  { to: "/reports", label: "Reports" }
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand-card">
        <h1>BloodDetect AI</h1>
        <p>Smart Blood Analysis</p>
      </div>
      <nav className="sidebar-nav">
        {links.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
