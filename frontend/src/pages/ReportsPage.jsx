import React from "react";

export default function ReportsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Reports</h2>
        <p>Download generated reports and use them for academic demonstration.</p>
      </div>
      <div className="card">
        <ul>
          <li>AI report should include patient information, confidence, certainty, risk level, and next-step suggestion.</li>
          <li>Add PDF export later using jsPDF on the frontend or WeasyPrint on the backend.</li>
          <li>Store report records in the database for long-term history.</li>
        </ul>
      </div>
    </div>
  );
}
