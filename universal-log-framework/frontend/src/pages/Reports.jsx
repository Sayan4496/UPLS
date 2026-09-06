import { useState } from "react";
import { Download, FileJson, FileSpreadsheet, RefreshCw } from "lucide-react";

import { getEvents } from "../services/api";

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function Reports() {
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const exportEvents = async (format) => {
    try {
      setLoading(true);
      setStatus("");
      const response = await getEvents({ page: 1, limit: 100 });
      const events = response.events || [];
      if (!events.length) {
        setStatus("No events are available to export.");
        return;
      }
      if (format === "json") {
        downloadFile(JSON.stringify(events, null, 2), "ulps-events.json", "application/json");
      } else {
        const columns = ["event_timestamp", "source_ip", "destination_ip", "event_type", "severity", "action", "message"];
        const csv = [columns.join(","), ...events.map((event) => columns.map((column) => JSON.stringify(event[column] ?? "")).join(","))].join("\n");
        downloadFile(csv, "ulps-events.csv", "text/csv");
      }
      setStatus(`${events.length} events exported as ${format.toUpperCase()}.`);
    } catch {
      setStatus("The event API is unavailable. Nothing was exported.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header"><div><p className="eyebrow">Portable evidence</p><h1>Reports</h1><p>Export the current event store without adding fabricated summaries or estimates.</p></div><span className="data-chip"><RefreshCw size={14} /> API-backed</span></div>
      {status && <div className="success-message">{status}</div>}
      <section className="report-grid">
        <button className="report-card" onClick={() => exportEvents("csv")} disabled={loading}><span className="report-icon green"><FileSpreadsheet size={24} /></span><span><strong>CSV event export</strong><small>Portable spreadsheet format from the latest 100 events.</small></span><Download size={17} /></button>
        <button className="report-card" onClick={() => exportEvents("json")} disabled={loading}><span className="report-icon blue"><FileJson size={24} /></span><span><strong>JSON event export</strong><small>Machine-readable normalized event records.</small></span><Download size={17} /></button>
      </section>
    </div>
  );
}

export default Reports;
