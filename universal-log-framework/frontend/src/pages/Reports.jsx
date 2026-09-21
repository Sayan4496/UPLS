import { useState } from "react";
import { Download, FileCode2, FileJson, FileSpreadsheet, RefreshCw } from "lucide-react";

import { exportEventsData } from "../services/api";

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

      const response = await exportEventsData(format);
      const contentType = response.headers["content-type"] || "application/octet-stream";
      const blob = response.data;

      if (!(blob instanceof Blob) || !blob.size) {
        setStatus(`No ${format.toUpperCase()} data was returned from the export endpoint.`);
        return;
      }

      const extension = format === "json" ? "json" : format === "csv" ? "csv" : "ndjson";
      const fileName = `ulps-events.${extension}`;
      const responseType = contentType.includes("json") ? "application/json" : contentType.includes("csv") ? "text/csv" : "application/x-ndjson";

      downloadFile(blob, fileName, responseType);
      setStatus(`Export completed: ${fileName}`);
    } catch (error) {
      console.error("Export failed", error);
      setStatus("The export API is unavailable. Nothing was exported.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header"><div><p className="eyebrow">Portable evidence</p><h1>Reports</h1><p>Export the current event store without adding fabricated summaries or estimates.</p></div><span className="data-chip"><RefreshCw size={14} /> API-backed</span></div>
      {status && <div className="success-message">{status}</div>}
      <section className="report-grid">
        <button className="report-card" onClick={() => exportEvents("csv")} disabled={loading}><span className="report-icon green"><FileSpreadsheet size={24} /></span><span><strong>CSV event export</strong><small>Portable spreadsheet format, limited to the latest 100 events.</small></span><Download size={17} /></button>
        <button className="report-card" onClick={() => exportEvents("json")} disabled={loading}><span className="report-icon blue"><FileJson size={24} /></span><span><strong>JSON event export</strong><small>Machine-readable normalized records, limited to the latest 100 events.</small></span><Download size={17} /></button>
        <button className="report-card" onClick={() => exportEvents("ndjson")} disabled={loading}><span className="report-icon purple"><FileCode2 size={24} /></span><span><strong>NDJSON event export</strong><small>Line-delimited records, limited to the latest 100 events.</small></span><Download size={17} /></button>
      </section>
    </div>
  );
}

export default Reports;
