import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import UploadView from "./UploadView.jsx";

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
    <div style={{ maxWidth: "600px", margin: "3rem auto", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Your Dashboard</h1>
        <button onClick={logout}>Logout</button>
      </div>

      <UploadView onUploadSuccess={fetchUploads} />

      {loading && <p>Loading your documents...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && !error && files.length === 0 && (
        <p>No files uploaded yet.</p>
      )}

      {!loading && !error && files.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {files.map((file) => (
            <li
              key={file.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div>
                <div>{file.filename}</div>
                <div style={{ fontSize: "0.85rem", color: "#666" }}>
                  {file.upload_date} — {file.status}
                </div>
              </div>
              <button
                onClick={() => handleDelete(file.id)}
                disabled={deletingId === file.id}
                style={{ color: "red", cursor: "pointer" }}
              >
                {deletingId === file.id ? "Deleting..." : "Delete"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}