import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import UploadView from "./UploadView.jsx";
import "./Dashboard.css";

export default function Dashboard() {
  const { token, logout } = useAuth();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  function fetchUploads() {
    setLoading(true);
    fetch("http://localhost:8000/uploads", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch uploads");
        return res.json();
      })
      .then((data) => {
        setFiles(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  function handleDelete(uploadId) {
    setDeletingId(uploadId);
    fetch(`http://localhost:8000/uploads/${uploadId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to delete file");
        setFiles((prev) => prev.filter((f) => f.id !== uploadId));
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setDeletingId(null);
      });
  }

  useEffect(() => {
    fetchUploads();
  }, [token]);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Your Dashboard</h1>
        <button className="dashboard-logout-btn" onClick={logout}>Logout</button>
      </div>

      <div className="dashboard-card">
        <h2 className="dashboard-section-title">Upload a File</h2>
        <UploadView onUploadSuccess={fetchUploads} />
      </div>

      <div className="dashboard-card">
        <h2 className="dashboard-section-title">Your Files</h2>

        {loading && <p className="dashboard-status-msg">Loading your documents...</p>}
        {error && <p className="dashboard-error-msg">{error}</p>}

        {!loading && !error && files.length === 0 && (
          <p className="dashboard-status-msg">No files uploaded yet.</p>
        )}

        {!loading && !error && files.length > 0 && (
          <ul className="dashboard-file-list">
            {files.map((file) => (
              <li key={file.id} className="dashboard-file-item">
                <div className="dashboard-file-info">
                  <span className="dashboard-file-name">{file.filename}</span>
                  <span className="dashboard-file-meta">
                    {file.upload_date}
                    <span className={`dashboard-status-badge ${file.status}`}>
                      {file.status}
                    </span>
                  </span>
                </div>
                <button
                  className="dashboard-delete-btn"
                  onClick={() => handleDelete(file.id)}
                  disabled={deletingId === file.id}
                >
                  {deletingId === file.id ? "Deleting..." : "Delete"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}