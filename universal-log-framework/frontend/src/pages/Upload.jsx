import { useState } from "react";
import { getProcessingJob, ingestLog, requestWithFallback } from "../services/api";

function Upload() {
  const [mode, setMode] = useState("file");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [processingJob, setProcessingJob] = useState(null);
  const [directForm, setDirectForm] = useState({
    source: "",
    timestamp: "",
    message: "",
    structuredData: "",
  });

  const handleFileChange = (event) => {
    setSelectedFiles(Array.from(event.target.files || []));
    setMessage("");
    setResult(null);
    setProcessingJob(null);
  };

  const handleModeChange = (nextMode) => {
    setMode(nextMode);
    setMessage("");
    setResult(null);
    setProcessingJob(null);
  };

  const handleDirectChange = (event) => {
    const { name, value } = event.target;
    setDirectForm((current) => ({ ...current, [name]: value }));
    setMessage("");
    setResult(null);
  };

  const clearDirectForm = () => {
    setDirectForm({ source: "", timestamp: "", message: "", structuredData: "" });
    setMessage("");
    setResult(null);
    setProcessingJob(null);
  };

  const waitForJob = async (jobId) => {
    let job = await getProcessingJob(jobId);
    setProcessingJob(job);

    while (job.status === "queued" || job.status === "processing") {
      await new Promise((resolve) => setTimeout(resolve, 500));
      job = await getProcessingJob(jobId);
      setProcessingJob(job);
    }

    return job;
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) {
      setMessage("Please select at least one log file.");
      return;
    }

    const formData = new FormData();
    const endpoint = selectedFiles.length === 1 ? "/upload/" : "/upload/batch";

    selectedFiles.forEach((file) => {
      if (selectedFiles.length === 1) {
        formData.append("file", file);
      } else {
        formData.append("files", file);
      }
    });

    try {
      setUploading(true);
      setMessage("");

      const response = await requestWithFallback(endpoint, {
        method: "post",
        data: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (selectedFiles.length > 1) {
        const completedJob = await waitForJob(response.data.job_id);
        setResult({ job: completedJob });
        setMessage(
          completedJob.status === "done"
            ? "Batch processed successfully."
            : "Batch completed with failures."
        );
      } else {
        setResult(response.data);
        setProcessingJob(response.data.job);
      }

      setMessage(
        selectedFiles.length === 1
          ? "File uploaded and processed successfully."
          : "Files uploaded and processed successfully."
      );

    } catch (error) {

      console.error(error);

      if (error.response) {
        setMessage(
          error.response.data.detail ||
          "Upload failed."
        );
      } else {
        setMessage(
          "Cannot connect to backend server."
        );
      }

    } finally {
      setUploading(false);
    }
  };

  const handleDirectIngest = async () => {
    if (!directForm.message.trim()) {
      setMessage("Enter a log message before ingesting.");
      setResult(null);
      return;
    }

    let structuredFields = {};
    if (directForm.structuredData.trim()) {
      try {
        structuredFields = JSON.parse(directForm.structuredData);
      } catch {
        setMessage("Structured data must be valid JSON.");
        setResult(null);
        return;
      }

      if (!structuredFields || Array.isArray(structuredFields) || typeof structuredFields !== "object") {
        setMessage("Structured data must be a JSON object.");
        setResult(null);
        return;
      }
    }

    const payload = {
      ...structuredFields,
      message: directForm.message,
    };

    if (directForm.source.trim()) payload.source = directForm.source.trim();
    if (directForm.timestamp.trim()) payload.timestamp = directForm.timestamp.trim();

    try {
      setUploading(true);
      setMessage("");
      const response = await ingestLog(payload);
      setResult(response);
      setProcessingJob(response.job || null);
      setMessage(response.message || "Log accepted for processing.");

      if (response.job?.job_id) {
        const completedJob = await waitForJob(response.job.job_id);
        setProcessingJob(completedJob);
        setMessage(
          completedJob.status === "done"
            ? "Log processed successfully."
            : `Log processing ${completedJob.status}.`
        );
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      const validationMessage = Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join("; ")
        : detail;
      setResult(null);
      setMessage(validationMessage || (error.response
        ? "The backend could not ingest this event."
        : "Cannot connect to backend server."));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page">

      <div className="page-header">
        <div>
          <h1>Ingestion</h1>

          <p>
            Choose a file workflow or send one API-style event.
          </p>
        </div>
      </div>

      <div className="ingestion-mode-tabs" role="tablist" aria-label="Ingestion mode">
        <button
          className={mode === "file" ? "ingestion-mode-tab active" : "ingestion-mode-tab"}
          onClick={() => handleModeChange("file")}
          role="tab"
          aria-selected={mode === "file"}
        >
          File Upload
        </button>
        <button
          className={mode === "direct" ? "ingestion-mode-tab active" : "ingestion-mode-tab"}
          onClick={() => handleModeChange("direct")}
          role="tab"
          aria-selected={mode === "direct"}
        >
          Direct Ingestion
        </button>
      </div>

      <p className="ingestion-help">
        Use File Upload for batch log files. Use Direct Ingestion for API-based event ingestion and integration testing.
        Direct Ingestion is intended for individual/API-style events. For large log files, use File Upload.
      </p>

      <div className="upload-container">

        {mode === "file" ? <div className="upload-card">

          <div className="upload-icon">
            ↑
          </div>

          <h2>Upload Log File</h2>

          <p>
            Upload a single file or a batch of log files.
          </p>

          <input
            type="file"
            multiple
            onChange={handleFileChange}
          />

          {selectedFiles.length > 0 && (
            <div className="selected-file">

              <strong>
                {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""} selected
              </strong>

              <span>
                {selectedFiles.map((file) => file.name).join(", ")}
              </span>

            </div>
          )}

          <button
            className="primary-button"
            onClick={handleUpload}
            disabled={uploading}
          >

            {uploading
              ? "Processing..."
              : selectedFiles.length > 1
                ? "Upload Batch"
                : "Upload & Process"}

          </button>

          {message && (

            <div
              className={
                result
                  ? "success-message"
                  : "error-message"
              }
            >

              {message}

            </div>

          )}

          {processingJob && (
            <div className="processing-job" aria-live="polite">
              <div className="processing-job-header">
                <strong>Job ID {processingJob.job_id}</strong>
                <span>{processingJob.status}</span>
              </div>

              <div className="processing-progress-track">
                <div
                  className="processing-progress-value"
                  style={{ width: `${processingJob.progress_percent}%` }}
                />
              </div>

              <div className="processing-job-stats">
                <span>Files {processingJob.files}</span>
                <span>Processed {processingJob.processed}</span>
                <span>Failed {processingJob.failed}</span>
                <span>Remaining {processingJob.remaining}</span>
                <span>Records {processingJob.records}</span>
              </div>

              <div className="processing-job-times">
                <span>Started {processingJob.started_at || "Queued"}</span>
                <span>Completed {processingJob.completed_at || "In progress"}</span>
              </div>

              <small>{processingJob.progress_percent}% complete</small>
            </div>
          )}

        </div> : <div className="upload-card direct-ingestion-card">
          <div className="upload-icon">⇢</div>
          <h2>Direct Ingestion</h2>
          <p>Send one event to the existing API ingestion endpoint.</p>

          <label htmlFor="direct-source">Source</label>
          <input
            id="direct-source"
            name="source"
            type="text"
            value={directForm.source}
            onChange={handleDirectChange}
            placeholder="Optional source or device type"
          />

          <label htmlFor="direct-timestamp">Timestamp</label>
          <input
            id="direct-timestamp"
            name="timestamp"
            type="text"
            value={directForm.timestamp}
            onChange={handleDirectChange}
            placeholder="Optional ISO 8601 timestamp"
          />

          <label htmlFor="direct-message">Log Message</label>
          <textarea
            id="direct-message"
            name="message"
            value={directForm.message}
            onChange={handleDirectChange}
            rows="6"
            placeholder="Enter one log message"
            required
          />

          <label htmlFor="direct-structured-data">Structured Data / JSON</label>
          <textarea
            id="direct-structured-data"
            name="structuredData"
            value={directForm.structuredData}
            onChange={handleDirectChange}
            rows="5"
            placeholder={'Optional JSON object, for example: {"severity":"high"}'}
          />

          <div className="direct-ingestion-actions">
            <button className="primary-button" onClick={handleDirectIngest} disabled={uploading}>
              {uploading ? "Ingesting..." : "Ingest Event"}
            </button>
            <button className="secondary-button" onClick={clearDirectForm} disabled={uploading}>
              Clear
            </button>
          </div>

          {message && <div className={result ? "success-message" : "error-message"}>{message}</div>}

          {processingJob && (
            <div className="processing-job" aria-live="polite">
              <div className="processing-job-header">
                <strong>Job ID {processingJob.job_id}</strong>
                <span>{processingJob.status}</span>
              </div>
              <div className="processing-job-stats">
                <span>Message {processingJob.message_id || result?.message_id || "Pending"}</span>
                <span>Records {processingJob.records}</span>
                <span>Failed {processingJob.failed}</span>
              </div>
            </div>
          )}
        </div>}


        {result && (

          <div className="result-card">

            <h2>Processing Result</h2>

            <div className="result-grid">

              {result.filename && (
                <div>
                  <span>Filename</span>

                  <strong>
                    {result.filename}
                  </strong>
                </div>
              )}

              {result.file_type && (
                <div>
                  <span>File Type</span>

                  <strong>
                    {result.file_type}
                  </strong>
                </div>
              )}

              {result.upload_id && (
                <div>
                  <span>Upload ID</span>

                  <strong>
                    {result.upload_id}
                  </strong>
                </div>
              )}

              {result.summary && (
                <div>
                  <span>Files Processed</span>

                  <strong>
                    {result.summary.files_processed}
                  </strong>
                </div>
              )}

            </div>

            {result.summary && (
              <div className="result-grid">
                <div>
                  <span>Total Raw Events</span>
                  <strong>{result.summary.total_raw_events_created}</strong>
                </div>

                <div>
                  <span>Total Normalized</span>
                  <strong>{result.summary.total_normalized_events_created}</strong>
                </div>

                <div>
                  <span>Duplicate Events</span>
                  <strong>{result.summary.total_duplicate_events}</strong>
                </div>
              </div>
            )}

            {result.job && (
              <div className="result-grid">
                <div>
                  <span>Job Status</span>
                  <strong>{result.job.status}</strong>
                </div>

                <div>
                  <span>Started</span>
                  <strong>{result.job.started_at || "Queued"}</strong>
                </div>

                <div>
                  <span>Completed</span>
                  <strong>{result.job.completed_at || "In progress"}</strong>
                </div>
              </div>
            )}

            <pre>
              {JSON.stringify(
                result.processing_result || result.summary || result.uploads || result.job || result,
                null,
                2
              )}
            </pre>

          </div>

        )}

      </div>

    </div>
  );
}

export default Upload;