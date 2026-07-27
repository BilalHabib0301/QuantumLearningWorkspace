import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

function UploadView() {
  const { token } = useAuth();

  // This "box" remembers which file the user picked.
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState(""); // "", "uploading", "success", "error"
  const [message, setMessage] = useState("");

  // Runs automatically when the user picks a file using the file picker window.
  function handleFileChange(event) {
    const file = event.target.files[0];
    setSelectedFile(file);
    setStatus("");
    setMessage("");
  }

  // Runs when the user clicks the Upload button.
  // Sends the file to the backend, along with the auth token.
  async function handleUploadClick() {
    if (!selectedFile) {
      alert("Please choose a file first.");
      return;
    }

    setStatus("uploading");
    setMessage("");

    // Files must be sent as FormData, not JSON
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          // Note: don't set Content-Type manually here —
          // the browser sets the correct multipart boundary automatically.
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
    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Something went wrong while uploading.");
    }
  }

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Upload a File</h2>

      {/* File picker */}
      <input type="file" onChange={handleFileChange} accept=".pdf" />

      {/* Upload button */}
      <button
        onClick={handleUploadClick}
        style={{ marginLeft: "1rem" }}
        disabled={status === "uploading"}
      >
        {status === "uploading" ? "Uploading..." : "Upload"}
      </button>

      {/* Currently selected file */}
      {selectedFile && status !== "success" && (
        <p>Selected file: {selectedFile.name}</p>
      )}

      {/* Success / error message */}
      {message && (
        <p style={{ color: status === "error" ? "red" : "green" }}>
          {message}
        </p>
      )}
    </div>
  );
}

export default UploadView;