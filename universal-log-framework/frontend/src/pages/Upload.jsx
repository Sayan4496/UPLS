import { useState } from "react";
import { getProcessingJob, requestWithFallback } from "../services/api";

function Upload() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [processingJob, setProcessingJob] = useState(null);

  const handleFileChange = (event) => {
    setSelectedFiles(Array.from(event.target.files || []));
    setMessage("");
    setResult(null);
    setProcessingJob(null);
  };

  const waitForJob = async (jobId) => {
    let job = await getProcessingJob(jobId);
    setProcessingJob(job);

    while (job.status === "QUEUED" || job.status === "PROCESSING") {
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
          completedJob.status === "COMPLETED"
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

  return (
    <div className="page">

      <div className="page-header">
        <div>
          <h1>Log Upload</h1>

          <p>
            Upload log files for parsing and normalization.
          </p>
        </div>
      </div>

      <div className="upload-container">

        <div className="upload-card">

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

        </div>


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