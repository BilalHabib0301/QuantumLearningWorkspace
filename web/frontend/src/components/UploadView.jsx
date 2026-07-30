import { useState, useRef } from "react";
import { useAuth } from "../context/AuthContext.jsx";

function UploadView({ onUploadSuccess }) {
  const { token } = useAuth();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");

  function handleFileChange(event) {
    const file = event.target.files[0];
    setSelectedFile(file);
    setStatus("");
    setMessage("");
  }

  async function handleUploadClick() {
    if (!selectedFile) {
      alert("Please choose a file first.");
      return;
    }

    setStatus("uploading");
    setMessage("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Upload failed");
      }

      setStatus("success");
      setMessage(`"${selectedFile.name}" uploaded successfully!`);
      setSelectedFile(null);
      
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Something went wrong while uploading.");
    }
  }

  return (
    <div className="upload-container">
      <h3>Upload Document</h3>
      <p className="upload-subtitle">Add PDFs to your knowledge base</p>
      
      <div className="upload-controls">
        <label className="file-input-label">
          <span>{selectedFile ? "Change File" : "Choose PDF"}</span>
          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileChange} 
            accept=".pdf" 
            className="file-input-hidden"
          />
        </label>

        <button
          onClick={handleUploadClick}
          className="upload-submit-btn"
          disabled={status === "uploading" || !selectedFile}
        >
          {status === "uploading" ? "Uploading..." : "Upload"}
        </button>
      </div>

      {selectedFile && status !== "success" && (
        <div className="selected-file-info">
          <span className="file-info-icon">📄</span>
          <span className="file-info-name" title={selectedFile.name}>{selectedFile.name}</span>
        </div>
      )}

      {message && (
        <div className={`upload-msg ${status === "error" ? "error-msg" : "success-msg"}`}>
          {message}
        </div>
      )}
    </div>
  );
}

export default UploadView;