import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import UploadView from "./UploadView.jsx";
import ChatInterface from "./ChatInterface.jsx";
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
      {/* Sidebar - left */}
      <aside className="dashboard-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <span className="logo-icon">🧠</span>
            <span className="logo-text">StudyMind <span>AI</span></span>
          </div>
        </div>

        <div className="sidebar-content">
          {/* Uploader */}
          <div className="sidebar-section">
            <UploadView onUploadSuccess={fetchUploads} />
          </div>

          {/* Files List */}
          <div className="sidebar-section files-section">
            <div className="section-header">
              <h4>Knowledge Library</h4>
              <button className="btn-refresh" onClick={fetchUploads} title="Refresh library">
                🔄
              </button>
            </div>
            
            {loading && <p className="status-text">Loading library...</p>}
            {error && <p className="status-text error-text">{error}</p>}

            {!loading && !error && files.length === 0 && (
              <div className="empty-library">
                <p>No documents uploaded yet. Upload a PDF above to build your knowledge base!</p>
              </div>
            )}

            {!loading && !error && files.length > 0 && (
              <div className="files-list-wrapper">
                <ul className="files-list">
                  {files.map((file, index) => (
                    <li key={index} className="file-item">
                      <span className="file-icon">📄</span>
                      <div className="file-details">
                        <span className="file-name" title={file.filename}>
                          {file.filename}
                        </span>
                        <span className="file-meta">
                          {file.file_type?.split("/")[1]?.toUpperCase() || "PDF"} • {new Date(file.upload_date).toLocaleDateString()}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Footer/Logout */}
        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">U</div>
            <div className="user-info">
              <span className="user-label">Active User</span>
            </div>
          </div>
          <button className="btn-logout" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      {/* Main Workspace - right */}
      <main className="dashboard-main">
        <ChatInterface key={token} />
      </main>
    </div>
  );
}