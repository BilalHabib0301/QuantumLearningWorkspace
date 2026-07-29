import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

function UploadView({ onUploadSuccess }) {
  const { token } = useAuth();

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
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Something went wrong while uploading.");
    }
  }

  return (
    <div className="upload-view">
      <div className="upload-controls">
        <input
          className="upload-file-input"
          type="file"
          onChange={handleFileChange}
          accept=".pdf"
        />
        <button
          className="upload-btn"
          onClick={handleUploadClick}
          disabled={status === "uploading"}
        >
          {status === "uploading" ? "Uploading..." : "Upload"}
        </button>
      </div>

      {selectedFile && status !== "success" && (
        <p className="upload-selected-file">Selected file: {selectedFile.name}</p>
      )}

      {message && (
        <p className={`upload-message ${status === "error" ? "error" : "success"}`}>
          {message}
        </p>
      )}
    </div>
  );
}

export default UploadView;