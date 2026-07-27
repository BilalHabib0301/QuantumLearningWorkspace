import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import UploadView from "./UploadView.jsx";

export default function Dashboard() {
  const { token, logout } = useAuth();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
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
  }, [token]);

  return (
    <div style={{ maxWidth: "600px", margin: "3rem auto", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Your Dashboard</h1>
        <button onClick={logout}>Logout</button>
      </div>
       <UploadView />
      {loading && <p>Loading your documents...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && !error && files.length === 0 && (
        <p>No files uploaded yet.</p>
      )}

      {!loading && !error && files.length > 0 && (
        <ul>
          {files.map((file, index) => (
            <li key={index}>
              {file.filename} — {file.upload_date}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}