import { useState } from "react";
import { NavLink, Link } from "react-router-dom";

import { useReportContext } from "../App.jsx";
import { exportReportPdf } from "../pdf/exportPdf.jsx";

export default function Layout({ children }) {
  const { report } = useReportContext();

  const [exporting, setExporting] = useState(false);
  const canExport = Boolean(report && report.result) && !exporting;

  async function exportReport() {
    if (!canExport) return;
    setExporting(true);

    try {
      await exportReportPdf(report);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark">V</span>
          <span className="brand-name">VERITY</span>
          <span className="brand-sub">/ AI</span>
        </Link>

        <nav className="nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              "nav-link" + (isActive ? " active" : "")
            }
          >
            Ask
          </NavLink>
          <NavLink
            to="/history"
            className={({ isActive }) =>
              "nav-link" + (isActive ? " active" : "")
            }
          >
            History
          </NavLink>
          <button
            type="button"
            className="nav-link nav-button"
            onClick={exportReport}
            disabled={!canExport}
            title={
              canExport
                ? "Download this report as a PDF"
                : "Open a report to export it"
            }
          >
            {exporting ? "Preparing…" : "Export"}
          </button>
        </nav>
      </header>

      <main className="page">{children}</main>

      <footer className="footer">
        <span>VERITY / AI — multi-model answer validation</span>
      </footer>
    </div>
  );
}
