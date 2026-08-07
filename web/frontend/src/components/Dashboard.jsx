import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import SettingsView from "./SettingsView.jsx";
import "./Dashboard.css";
import DocumentPreviewModal from "./DocumentPreviewModal.jsx";

// ─── Sub-Components ──────────────────────────────────────────────────────────

function SidebarNav({ activeTab, setActiveTab }) {
  const { logout, userEmail } = useAuth();
  const initial = userEmail ? userEmail[0].toUpperCase() : "U";

  const navItems = [
    { id: "documents", icon: "📄", label: "Documents" },
    { id: "chat", icon: "💬", label: "AI Chat" },
    { id: "graph", icon: "🗺️", label: "Knowledge Graph" },
    { id: "settings", icon: "⚙️", label: "Settings" },
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
        <div
          className="user-avatar-circle"
          onClick={() => setActiveTab("settings")}
          title={`${userEmail || "User"} (Click for Settings)`}
          style={{ cursor: "pointer" }}
        >
          {initial}
        </div>
        <button className="logout-icon-btn" onClick={logout} title="Logout">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
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
    settings: {
      title: "Account Settings",
      subtitle: "Manage your profile, session security, and workspace preferences",
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

function DocumentsView({ onAskAboutDocument }) {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [previewId, setPreviewId] = useState(null);

  const API_BASE = "http://localhost:8000";

  function fetchUploads(isSilent = false) {
    if (!isSilent) {
      setLoading(true);
      setError("");
    }
    fetch(`${API_BASE}/uploads`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to fetch uploads");
        return res.json();
      })
      .then((data) => {
        if (data) setFiles(data);
        if (!isSilent) setLoading(false);
      })
      .catch((err) => {
        if (!isSilent) setError(err.message);
        if (!isSilent) setLoading(false);
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
        if (handle401(res)) return;
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Upload failed");
        }
        return res.json();
      })
      .then((data) => {
        if (!data) return;
        setUploadMsg(`"${selectedFile.name}" uploaded successfully! Processing started...`);
        setUploadStatus("success");
        showToast(`"${selectedFile.name}" uploaded successfully!`, "success");
        setSelectedFile(null);
        fetchUploads(true);
      })
      .catch((err) => {
        setUploadMsg(err.message || "Something went wrong.");
        setUploadStatus("error");
        showToast(err.message || "Upload failed", "error");
      })
      .finally(() => {
        setUploading(false);
      });
  }

  function handleDelete(uploadId, filename) {
    setDeletingId(uploadId);
    fetch(`${API_BASE}/uploads/${uploadId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to delete file");
        setFiles((prev) => prev.filter((f) => f.id !== uploadId));
        showToast(`"${filename}" deleted`, "success");
      })
      .catch((err) => {
        setError(err.message);
        showToast(err.message || "Failed to delete file", "error");
      })
      .finally(() => {
        setDeletingId(null);
      });
  }

  useEffect(() => {
    fetchUploads();
    const interval = setInterval(() => {
      fetchUploads(true);
    }, 3000);

    return () => clearInterval(interval);
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
            <button className="btn-refresh" onClick={() => fetchUploads(false)} title="Refresh">
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
            <button onClick={() => fetchUploads(false)}>Retry</button>
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
              const statusRaw = (file.status || "Ready").toLowerCase();
              const isProcessing = statusRaw === "processing";
              const displayStatus = isProcessing ? "Processing" : "Ready";

              const getFileType = (mime, filename) => {
                if (mime && mime.includes("/")) {
                  const subtype = mime.split("/")[1]?.split(".")[0].toUpperCase() || "";
                  if (subtype.includes("OFFICE") || subtype.includes("WORD") || subtype.includes("OPENXML") || subtype.includes("VND")) {
                    return "DOCX";
                  }
                  if (subtype.length <= 6) return subtype;
                }
                const ext = filename.split(".").pop()?.toUpperCase() || "PDF";
                if (ext.length > 6) return "FILE";
                return ext;
              };

              return (
                <div
                  key={file.id}
                  className={`file-row ${isDeleting ? "deleting" : ""}`}
                >
                  <div className="file-icon-box">📄</div>
                  <div className="file-info">
                    <span className="file-name-text" title={file.filename}>
                      {file.filename}
                    </span>
                    <span className="file-type-text">
                      {getFileType(file.file_type, file.filename)}
                    </span>
                  </div>
                  <span className="file-date-text">
                    {file.upload_date
                      ? new Date(file.upload_date).toLocaleDateString("en-US", {
                          month: "short", day: "numeric", year: "numeric",
                        })
                      : "Unknown"}
                  </span>

                  <div className={`status-pill ${isProcessing ? "status-processing" : "status-ready"}`}>
                    <span className={`status-dot ${isProcessing ? "pulse-dot" : "solid-dot"}`}></span>
                    {displayStatus}
                  </div>

                  <button
                    className="btn-preview-file"
                    onClick={() => setPreviewId(file.id)}
                    title="Preview document details"
                  >
                    👁️
                  </button>

                  <button
                    className={`btn-ask-doc ${isProcessing ? "disabled" : ""}`}
                    onClick={() => !isProcessing && onAskAboutDocument(file.filename)}
                    disabled={isProcessing}
                    title={
                      isProcessing
                        ? "File is currently processing and not yet searchable"
                        : `Ask questions about ${file.filename}`
                    }
                  >
                    💬 Ask AI
                  </button>

                  <button
                    className="btn-delete-file"
                    onClick={() => handleDelete(file.id, file.filename)}
                    disabled={isDeleting}
                    title="Delete file"
                  >
                    {isDeleting ? (
                      <span className="mini-spinner"></span>
                    ) : (
                      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#ef4444" }}>
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        <line x1="10" y1="11" x2="10" y2="17" />
                        <line x1="14" y1="11" x2="14" y2="17" />
                      </svg>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewId && (
        <DocumentPreviewModal
          uploadId={previewId}
          onClose={() => setPreviewId(null)}
        />
      )}
    </div>
  );
}
function ChatView({ targetDocument, setTargetDocument }) {
  const { token, handle401 } = useAuth();
  const [files, setFiles] = useState([]);
  const [messages, setMessages] = useState([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const API_BASE = "http://localhost:8000";

  const welcomeMessage = {
    role: "assistant",
    content:
      "Hello! I'm your StudyMind AI assistant. Select a document or ask me anything about your uploaded study materials.",
    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };

  // Load past conversation from the backend when the chat page opens
  useEffect(() => {
    fetch(`${API_BASE}/chat-history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to load chat history");
        return res.json();
      })
      .then((data) => {
        if (data && data.length > 0) {
          const formatted = data.map((msg) => ({
            role: msg.role,
            content: msg.content,
            sources: msg.sources || [],
            timestamp: new Date(msg.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          }));
          setMessages(formatted);
        } else {
          setMessages([welcomeMessage]);
        }
        setHistoryLoaded(true);
      })
      .catch(() => {
        setMessages([welcomeMessage]);
        setHistoryLoaded(true);
      });
  }, [token]);

  // Save one message to the backend (fire-and-forget)
  function saveMessage(message) {
    fetch(`${API_BASE}/chat-history`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        role: message.role,
        content: message.content,
        sources: message.sources || null,
      }),
    }).catch(() => {
      // Silent fail — losing a history save shouldn't break the chat UX
    });
  }

  // Fetch uploads to populate document scope selector
  function fetchUploads() {
    fetch(`${API_BASE}/uploads`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (res.ok) return res.json();
      })
      .then((data) => {
        if (data) setFiles(data);
      })
      .catch(() => {});
  }

  useEffect(() => {
    fetchUploads();
    const interval = setInterval(fetchUploads, 3000);
    return () => clearInterval(interval);
  }, [token]);

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
    saveMessage(userMessage);
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
          filename: targetDocument || null,
        }),
      });

      if (handle401(response)) return;
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
      saveMessage(assistantMessage);
    } catch (err) {
      const errorMessage = {
        role: "assistant",
        content: "Sorry, I had trouble reaching the AI server. Please make sure the backend is running.",
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMessage]);
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
      fetch(`${API_BASE}/chat-history`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (handle401(res)) return;
          setMessages([welcomeMessage]);
        })
        .catch(() => {
          setMessages([welcomeMessage]);
        });
    }
  };

  return (
    <div className="chat-view">
      {/* Chat Header Bar */}
      <div className="chat-header-bar">
        <div className="chat-doc-selector-container">
          <span className="selector-icon">🎯 Scope:</span>
          <select
            value={targetDocument || ""}
            onChange={(e) => setTargetDocument(e.target.value || null)}
            className="chat-doc-select"
          >
            <option value="">All Searchable Documents</option>
            {files.map((file) => {
              const isProcessing = (file.status || "").toLowerCase() === "processing";
              return (
                <option key={file.id} value={file.filename} disabled={isProcessing}>
                  {file.filename} {isProcessing ? "⏳ (Processing - Not Searchable)" : "✓ (Ready)"}
                </option>
              );
            })}
          </select>
          {targetDocument && (
            <button
              className="btn-clear-target-doc"
              onClick={() => setTargetDocument(null)}
              title="Clear active document filter"
            >
              ✕ Clear Filter
            </button>
          )}
        </div>

        <div className="chat-header-right">
          <div className="chat-status-info">
            <span className="status-dot-green"></span>
            <span className="status-text">Online</span>
          </div>
          <button className="btn-clear-chat" onClick={clearHistory}>
            Clear
          </button>
        </div>
      </div>

      {targetDocument && (
        <div className="target-doc-banner">
          <span>Asking specifically about <strong>"{targetDocument}"</strong></span>
        </div>
      )}

      <div className="chat-messages-scroll" id="chat-messages-scroll">
        {!historyLoaded && <p className="modal-status-text">Loading conversation...</p>}

        {historyLoaded &&
          messages.map((msg, index) => (
            <div key={index} className={`msg-wrapper ${msg.role === "user" ? "msg-user" : "msg-ai"}`}>
              <div
                className={`msg-bubble ${
                  msg.role === "user" ? "bubble-user" : "bubble-ai"
                } ${msg.isError ? "bubble-error" : ""}`}
              >
                <div className="msg-content">{msg.content}</div>

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

      <form className="chat-input-bar" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            targetDocument
              ? `Ask a question about ${targetDocument}...`
              : "Ask a question about your documents... (Press Enter to send)"
          }
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
  const [targetDocument, setTargetDocument] = useState(null);

  const handleAskAboutDocument = (filename) => {
    setTargetDocument(filename);
    setActiveTab("chat");
  };

  return (
    <div className="app-shell">
      <SidebarNav activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="main-area">
        <TopBar activeTab={activeTab} />
        <div className="page-content">
          {activeTab === "documents" && (
            <DocumentsView onAskAboutDocument={handleAskAboutDocument} />
          )}
          {activeTab === "chat" && (
            <ChatView
              targetDocument={targetDocument}
              setTargetDocument={setTargetDocument}
            />
          )}
          {activeTab === "graph" && <GraphView />}
          {activeTab === "settings" && <SettingsView />}
        </div>
      </div>
    </div>
  );
}