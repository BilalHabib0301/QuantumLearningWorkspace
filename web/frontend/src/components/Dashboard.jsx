import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./Dashboard.css";

// ─── Sub-Components ──────────────────────────────────────────────────────────

function SidebarNav({ activeTab, setActiveTab }) {
  const { logout } = useAuth();

  const navItems = [
    { id: "documents", icon: "📄", label: "Documents" },
    { id: "chat", icon: "💬", label: "AI Chat" },
    { id: "graph", icon: "🗺️", label: "Knowledge Graph" },
  ];

  return (
    <aside className="sidebar-nav">
      {/* Logo */}
      <div className="sidebar-logo-area">
        <span className="logo-icon">🧠</span>
      </div>

      {/* Navigation Items */}
      <nav className="sidebar-nav-items">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-btn ${activeTab === item.id ? "active" : ""}`}
            onClick={() => setActiveTab(item.id)}
            title={item.label}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-tooltip">{item.label}</span>
            {activeTab === item.id && <span className="nav-indicator"></span>}
          </button>
        ))}
      </nav>

      {/* Bottom: User + Logout */}
      <div className="sidebar-bottom">
        <div className="user-avatar-circle">U</div>
        <button className="logout-icon-btn" onClick={logout} title="Logout">
          🚪
        </button>
      </div>
    </aside>
  );
}

function TopBar({ activeTab }) {
  const pageTitles = {
    documents: {
      title: "Your Dashboard",
      subtitle: "Upload, manage, and interact with your study materials",
    },
    chat: {
      title: "AI Assistant",
      subtitle: "Ask questions about your uploaded study materials",
    },
    graph: {
      title: "Knowledge Graph",
      subtitle: "Visualize connections between concepts in your materials",
    },
  };

  const { title, subtitle } = pageTitles[activeTab] || pageTitles.documents;

  return (
    <header className="top-bar">
      <div className="top-bar-info">
        <h1 className="top-bar-title">{title}</h1>
        <p className="top-bar-subtitle">{subtitle}</p>
      </div>
      <div className="top-bar-user">
        <div className="user-badge">
          <span className="user-badge-avatar">U</span>
          <span className="user-badge-name">Active User</span>
        </div>
      </div>
    </header>
  );
}

function DocumentsView() {
  const { token } = useAuth();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");

  const API_BASE = "http://localhost:8000";

  function fetchUploads() {
    setLoading(true);
    setError("");
    fetch(`${API_BASE}/uploads`, {
      headers: { Authorization: `Bearer ${token}` },
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

  function handleUpload() {
    if (!selectedFile) {
      setUploadMsg("Please choose a file first.");
      setUploadStatus("error");
      return;
    }

    setUploading(true);
    setUploadMsg("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    fetch(`${API_BASE}/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Upload failed");
        }
        return res.json();
      })
      .then(() => {
        setUploadMsg(`"${selectedFile.name}" uploaded successfully!`);
        setUploadStatus("success");
        setSelectedFile(null);
        setUploadStatus("");
        fetchUploads();
      })
      .catch((err) => {
        setUploadMsg(err.message || "Something went wrong.");
        setUploadStatus("error");
      })
      .finally(() => {
        setUploading(false);
      });
  }

  function handleDelete(uploadId) {
    setDeletingId(uploadId);
    fetch(`${API_BASE}/uploads/${uploadId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
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
    <div className="documents-view">
      {/* Upload Card */}
      <div className="upload-card">
        <h3>Upload Document</h3>
        <p className="upload-subtitle">Add PDFs, documents, or lecture notes to your knowledge base</p>
        <div className="upload-row">
          <label className="file-input-label">
            <span>{selectedFile ? selectedFile.name : "Choose File"}</span>
            <input
              type="file"
              onChange={(e) => {
                setSelectedFile(e.target.files[0]);
                setUploadMsg("");
                setUploadStatus("");
              }}
              accept=".pdf,.txt,.doc,.docx"
              className="file-input-hidden"
            />
          </label>
          <button
            className="upload-submit-btn"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
        {uploadMsg && (
          <div className={`upload-msg ${uploadStatus === "error" ? "error-msg" : "success-msg"}`}>
            {uploadMsg}
          </div>
        )}
      </div>

      {/* File List */}
      <div className="file-list-card">
        <div className="file-list-header">
          <h3>Knowledge Library</h3>
          <div className="header-actions">
            <span className="file-count-badge">{files.length} file{files.length !== 1 ? "s" : ""}</span>
            <button className="btn-refresh" onClick={fetchUploads} title="Refresh">
              🔄
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading-state">
            <div className="loading-dots">
              <span></span><span></span><span></span>
            </div>
            <p className="loading-text">Loading your documents...</p>
            <p className="loading-subtext">Fetching your uploaded study materials</p>
          </div>
        )}

        {!loading && error && (
          <div className="error-state">
            <p>{error}</p>
            <button onClick={fetchUploads}>Retry</button>
          </div>
        )}

        {!loading && !error && files.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">📚</span>
            <p className="empty-title">No documents yet</p>
            <p className="empty-subtitle">Upload your first PDF to get started</p>
          </div>
        )}

        {!loading && !error && files.length > 0 && (
          <div className="file-rows">
            {files.map((file) => {
              const isDeleting = deletingId === file.id;
              return (
                <div
                  key={file.id}
                  className={`file-row ${isDeleting ? "deleting" : ""}`}
                >
                  <div className="file-row-left">
                    <div className="file-icon-box">📄</div>
                    <div className="file-info">
                      <span className="file-name-text" title={file.filename}>
                        {file.filename}
                      </span>
                      <span className="file-type-text">
                        {(file.file_type || "PDF").split("/")[1]?.toUpperCase() || "PDF"}
                      </span>
                    </div>
                  </div>
                  <span className="file-date-text">
                    {file.upload_date
                      ? new Date(file.upload_date).toLocaleDateString("en-US", {
                          month: "short", day: "numeric", year: "numeric",
                        })
                      : "Unknown"}
                  </span>
                  <div className="status-pill">
                    <span className="status-dot"></span>
                    {file.status || "Processed"}
                  </div>
                  <button
                    className="btn-delete-file"
                    onClick={() => handleDelete(file.id)}
                    disabled={isDeleting}
                    title="Delete file"
                  >
                    {isDeleting ? <span className="mini-spinner"></span> : "🗑"}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatView() {
  const { token } = useAuth();
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem("studymind_chat_history");
    return saved
      ? JSON.parse(saved)
      : [
          {
            role: "assistant",
            content:
              "Hello! I'm your StudyMind AI assistant. Ask me anything about your uploaded study materials, and I'll find the answers for you.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ];
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const API_BASE = "http://localhost:8000";

  // Save history
  useEffect(() => {
    localStorage.setItem("studymind_chat_history", JSON.stringify(messages));
  }, [messages]);

  const scrollToBottom = () => {
    const container = document.getElementById("chat-messages-scroll");
    if (container) container.scrollTop = container.scrollHeight;
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const apiHistory = messages.map((msg) => ({
      role: msg.role === "assistant" ? "assistant" : "user",
      content: msg.content,
    }));

    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: userMessage.content,
          history: apiHistory,
          top_k: 4,
          include_sources: true,
        }),
      });

      if (!response.ok) throw new Error("Failed to connect to AI server");

      const data = await response.json();

      const assistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        timing: data.timing || null,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I had trouble reaching the AI server. Please make sure the backend is running.",
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearHistory = () => {
    if (window.confirm("Are you sure you want to clear your conversation history?")) {
      const initial = [
        {
          role: "assistant",
          content:
            "Hello! I'm your StudyMind AI assistant. Ask me anything about your uploaded study materials, and I'll find the answers for you.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ];
      setMessages(initial);
      localStorage.removeItem("studymind_chat_history");
    }
  };

  return (
    <div className="chat-view">
      {/* Chat Header */}
      <div className="chat-header-bar">
        <div className="chat-status-info">
          <span className="status-dot-green"></span>
          <span className="status-text">Online</span>
        </div>
        <button className="btn-clear-chat" onClick={clearHistory}>
          Clear
        </button>
      </div>

      {/* Messages */}
      <div className="chat-messages-scroll" id="chat-messages-scroll">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`msg-wrapper ${msg.role === "user" ? "msg-user" : "msg-ai"}`}
          >
            <div
              className={`msg-bubble ${
                msg.role === "user" ? "bubble-user" : "bubble-ai"
              } ${msg.isError ? "bubble-error" : ""}`}
            >
              <div className="msg-content">{msg.content}</div>

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="msg-sources">
                  <span className="sources-title">🔍 Sources:</span>
                  <div className="sources-list">
                    {msg.sources.map((src, i) => (
                      <span key={i} className="source-chip" title={src.chunk}>
                        {src.document}
                      </span>
                    ))}
                  </div>
                  {msg.timing && (
                    <span className="source-speed">
                      Grounded in {msg.timing.total_ms}ms (LLM: {msg.timing.llm_ms}ms)
                    </span>
                  )}
                </div>
              )}

              <span className="msg-time">{msg.timestamp}</span>
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="msg-wrapper msg-ai">
            <div className="msg-bubble bubble-ai typing-bubble">
              <div className="typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form className="chat-input-bar" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents... (Press Enter to send)"
          className="chat-text-input"
          disabled={isLoading}
        />
        <button type="submit" className="btn-send-chat" disabled={!input.trim() || isLoading}>
          ➤
        </button>
      </form>
    </div>
  );
}

function GraphView() {
  return (
    <div className="graph-view">
      <div className="graph-placeholder">
        <span className="graph-icon">🗺️</span>
        <h3 className="graph-title">Knowledge Graph</h3>
        <p className="graph-desc">
          Visualize connections between concepts extracted from your study materials.
          Upload more documents to generate your personalized knowledge graph with topic
          relationships and concept maps.
        </p>
      </div>
    </div>
  );
}

// ─── Main Dashboard Export ───────────────────────────────────────────────────

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("documents");

  return (
    <div className="app-shell">
      <SidebarNav activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="main-area">
        <TopBar activeTab={activeTab} />
        <div className="page-content">
          {activeTab === "documents" && <DocumentsView />}
          {activeTab === "chat" && <ChatView />}
          {activeTab === "graph" && <GraphView />}
        </div>
      </div>
    </div>
  );
}
