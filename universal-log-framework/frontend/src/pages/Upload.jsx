import { useState } from "react";
import axios from "axios";

function Upload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage("");
    setResult(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage("Please select a log file first.");
      return;
    }

    const formData = new FormData();

    formData.append("file", selectedFile);

    try {
      setUploading(true);
      setMessage("");

      const response = await axios.post(
        "http://127.0.0.1:8000/upload/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setResult(response.data);

      setMessage("File uploaded and processed successfully.");

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
            Supported formats depend on your backend configuration.
          </p>

          <input
            type="file"
            onChange={handleFileChange}
          />

          {selectedFile && (
            <div className="selected-file">

              <strong>
                {selectedFile.name}
              </strong>

              <span>
                {(selectedFile.size / 1024).toFixed(2)} KB
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

        </div>


        {result && (

          <div className="result-card">

            <h2>Processing Result</h2>

            <div className="result-grid">

              <div>
                <span>Filename</span>

                <strong>
                  {result.filename}
                </strong>
              </div>

              <div>
                <span>File Type</span>

                <strong>
                  {result.file_type}
                </strong>
              </div>

              <div>
                <span>Upload ID</span>

                <strong>
                  {result.upload_id}
                </strong>
              </div>

            </div>

            <pre>
              {JSON.stringify(
                result.processing_result,
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