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

  const historyRows = jobs.flatMap((job) => {
    if (job.details?.length) {
      return job.details.map((detail, index) => (
        <tr key={`${job.job_id}-${index}`} onClick={() => setSelectedJob(job)}>
          <td className="job-id-cell">{job.job_id.slice(0, 8)}</td>
          <td>{detail.file}</td>
          <td>{detail.format}</td>
          <td>{detail.records.toLocaleString()}</td>
          <td>{detail.success.toLocaleString()}</td>
          <td>{detail.failed.toLocaleString()}</td>
          <td><span className={`job-status ${detail.status.toLowerCase()}`}>{detail.status}</span></td>
          <td>{detail.processing_time}s</td>
        </tr>
      ));
    }

    return [
      <tr key={job.job_id} onClick={() => setSelectedJob(job)}>
        <td className="job-id-cell">{job.job_id.slice(0, 8)}</td>
        <td>{job.files} file(s)</td>
        <td>-</td>
        <td>{job.records.toLocaleString()}</td>
        <td>{job.processed_records.toLocaleString()}</td>
        <td>{job.failed_records.toLocaleString()}</td>
        <td><span className={`job-status ${job.status.toLowerCase()}`}>{job.status}</span></td>
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
              <div><p className="eyebrow">Processing evidence</p><h2>Job {selectedJob.job_id}</h2></div>
              <button className="icon-button" onClick={() => setSelectedJob(null)} aria-label="Close job details"><X size={18} /></button>
            </div>
            <div className="history-detail-grid">
              <span>Status<strong>{selectedJob.status}</strong></span>
              <span>Files<strong>{selectedJob.files}</strong></span>
              <span>Records<strong>{selectedJob.records.toLocaleString()}</strong></span>
              <span>Processing time<strong>{selectedJob.processing_time}s</strong></span>
              <span>Started<strong>{selectedJob.started_at || "-"}</strong></span>
              <span>Completed<strong>{selectedJob.completed_at || "-"}</strong></span>
            </div>
            {selectedJob.details?.map((detail) => (
              <section className="history-evidence-card" key={`${selectedJob.job_id}-${detail.file}`}>
                <h3>{detail.file}</h3>
                <div className="history-detail-grid">
                  <span>Raw records<strong>{detail.records}</strong></span>
                  <span>Parsed records<strong>{detail.records}</strong></span>
                  <span>Normalized records<strong>{detail.success}</strong></span>
                  <span>Failed records<strong>{detail.failed}</strong></span>
                  <span>Quality score<strong>{detail.quality_score}%</strong></span>
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
