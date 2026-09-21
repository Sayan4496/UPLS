import { useEffect, useState } from "react";
import { Clock3, RefreshCw, X } from "lucide-react";

import { getProcessingJobs } from "../services/api";

function ProcessingHistory() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getProcessingJobs();
      setJobs(data.jobs || []);
    } catch {
      setError("Unable to load processing history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadJobs();
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  const numberValue = (value) => Number(value || 0).toLocaleString();
  const jobId = (job) => job.job_id || job.message_id || "unknown";
  const statusValue = (value, fallback = "unknown") => String(value || fallback);

  const historyRows = jobs.flatMap((job) => {
    if (job.details?.length) {
      return job.details.map((detail, index) => (
        <tr key={`${jobId(job)}-${index}`} onClick={() => setSelectedJob(job)}>
          <td className="job-id-cell">{jobId(job).slice(0, 8)}</td>
          <td>{detail.file || `${detail.format || "Unknown"} record batch`}</td>
          <td>{detail.format}</td>
          <td>{numberValue(detail.records)}</td>
          <td>{numberValue(detail.success ?? detail.normalized ?? job.processed_records)}</td>
          <td>{numberValue(detail.failed)}</td>
          <td><span className={`job-status ${statusValue(detail.status, job.status).toLowerCase()}`}>{statusValue(detail.status, job.status)}</span></td>
          <td>{detail.processing_time ?? job.processing_time ?? 0}s</td>
        </tr>
      ));
    }

    return [
      <tr key={jobId(job)} onClick={() => setSelectedJob(job)}>
        <td className="job-id-cell">{jobId(job).slice(0, 8)}</td>
        <td>{job.files} file(s)</td>
        <td>-</td>
        <td>{numberValue(job.records)}</td>
        <td>{numberValue(job.processed_records ?? job.processed)}</td>
        <td>{numberValue(job.failed_records)}</td>
        <td><span className={`job-status ${statusValue(job.status).toLowerCase()}`}>{statusValue(job.status)}</span></td>
        <td>{job.processing_time}s</td>
      </tr>
    ];
  });

  return (
    <div className="page processing-history-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Trace every run</p>
          <h1>Processing History</h1>
          <p>Review batch jobs, quality results, and parser evidence.</p>
        </div>
        <button className="secondary-button" onClick={loadJobs} disabled={loading}>
          <RefreshCw size={16} /> Refresh history
        </button>
      </div>

      {error && <div className="connection-error"><strong>History unavailable</strong><p>{error}</p></div>}

      <section className="panel processing-history-panel">
        {loading ? (
          <div className="loading-state"><div className="loader" /> Loading processing history...</div>
        ) : jobs.length === 0 ? (
          <div className="empty-state"><Clock3 size={24} /><h3>No processing jobs yet</h3><p>Upload a log file to create the first processing record.</p></div>
        ) : (
          <div className="processing-history-table-wrap">
            <table className="processing-history-table">
              <thead>
                <tr>
                  <th>Job ID</th><th>File</th><th>Format</th><th>Records</th><th>Success</th><th>Failed</th><th>Status</th><th>Time</th>
                </tr>
              </thead>
              <tbody>
                {historyRows}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedJob && (
        <div className="history-detail-backdrop" onClick={() => setSelectedJob(null)}>
          <aside className="history-detail-panel" onClick={(event) => event.stopPropagation()}>
            <div className="panel-header">
              <div><p className="eyebrow">Processing evidence</p><h2>Job {jobId(selectedJob)}</h2></div>
              <button className="icon-button" onClick={() => setSelectedJob(null)} aria-label="Close job details"><X size={18} /></button>
            </div>
            <div className="history-detail-grid">
              <span>Status<strong>{selectedJob.status}</strong></span>
              <span>Files<strong>{selectedJob.files}</strong></span>
              <span>Records<strong>{numberValue(selectedJob.records)}</strong></span>
              <span>Normalized<strong>{numberValue(selectedJob.processed_records)}</strong></span>
              <span>Failed<strong>{numberValue(selectedJob.failed_records)}</strong></span>
              <span>Processing time<strong>{selectedJob.processing_time}s</strong></span>
              <span>Started<strong>{selectedJob.started_at || "-"}</strong></span>
              <span>Completed<strong>{selectedJob.completed_at || "-"}</strong></span>
            </div>
            {selectedJob.details?.map((detail) => (
              <section className="history-evidence-card" key={`${jobId(selectedJob)}-${detail.file || detail.queue_offset}`}>
                <h3>{detail.file || `${detail.format || "Unknown"} record batch`}</h3>
                <div className="history-detail-grid">
                  <span>Raw records<strong>{numberValue(detail.records)}</strong></span>
                  <span>Parsed records<strong>{numberValue(detail.records)}</strong></span>
                  <span>Normalized records<strong>{numberValue(detail.success ?? detail.normalized ?? selectedJob.processed_records)}</strong></span>
                  <span>Failed records<strong>{numberValue(detail.failed)}</strong></span>
                  <span>Quality score<strong>{detail.quality_score ?? "-"}{detail.quality_score == null ? "" : "%"}</strong></span>
                  <span>Parser<strong>{detail.parser || "-"}</strong></span>
                  <span>Parser version<strong>{detail.parser_version || "-"}</strong></span>
                  <span>Processing time<strong>{detail.processing_time}s</strong></span>
                </div>
              </section>
            ))}
          </aside>
        </div>
      )}
    </div>
  );
}

export default ProcessingHistory;
