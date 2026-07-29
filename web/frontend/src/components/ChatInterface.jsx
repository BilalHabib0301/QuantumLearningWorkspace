import { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./ChatInterface.css";

// Helper to decode JWT token and extract email
const getEmailFromToken = (token) => {
  if (!token) return null;
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    return payload.sub || null;
  } catch (e) {
    return null;
  }
};

const getStorageKey = (token) => {
  const email = getEmailFromToken(token);
  return email ? `studymind_chat_history_${email}` : "studymind_chat_history_guest";
};

export default function ChatInterface() {
  const { token } = useAuth();
  const [messages, setMessages] = useState(() => {
    const key = getStorageKey(token);
    const saved = localStorage.getItem(key);
    return saved
      ? JSON.parse(saved)
      : [
          {
            role: "assistant",
            content: "Hello! I'm your StudyMind AI assistant. Ask me anything about your uploaded study materials, and I'll find the answers for you.",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ];
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Save history to localStorage whenever it changes
  useEffect(() => {
    const key = getStorageKey(token);
    localStorage.setItem(key, JSON.stringify(messages));
  }, [messages, token]);

  // Auto-scroll to the bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Format chat history for the API contract
    const apiHistory = messages.map(msg => ({
      role: msg.role === "assistant" ? "assistant" : "user",
      content: msg.content
    }));

    try {
      const response = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          question: userMessage.content,
          history: apiHistory,
          top_k: 4,
          include_sources: true
        })
      });

      if (!response.ok) {
        throw new Error("Failed to connect to AI server");
      }

      const data = await response.json();
      
      const assistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        timing: data.timing || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I had trouble reaching the AI server. Please make sure the backend is running.",
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
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
          content: "Hello! I'm your StudyMind AI assistant. Ask me anything about your uploaded study materials, and I'll find the answers for you.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ];
      setMessages(initial);
      const key = getStorageKey(token);
      localStorage.removeItem(key);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="chat-header-info">
          <h3>AI Tutor Chat</h3>
          <span className="chat-status">
            <span className="status-dot"></span> Online
          </span>
        </div>
        <button className="btn-clear" onClick={clearHistory} title="Clear history">
          🗑️ Clear
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message-wrapper ${msg.role === "user" ? "user-wrapper" : "assistant-wrapper"}`}
          >
            <div className={`message-bubble ${msg.role === "user" ? "user-bubble" : "assistant-bubble"} ${msg.isError ? "error-bubble" : ""}`}>
              <div className="message-content">{msg.content}</div>
              
              {/* Show sources if present (Premium feature) */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <span className="sources-title">🔍 Sources:</span>
                  <div className="sources-list">
                    {msg.sources.map((src, i) => (
                      <span key={i} className="source-tag" title={src.chunk}>
                        {src.document}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Show generation time if present */}
              {msg.timing && (
                <div className="message-meta-info">
                  Grounded in {msg.timing.total_ms}ms (LLM: {msg.timing.llm_ms}ms)
                </div>
              )}

              <span className="message-time">{msg.timestamp}</span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper assistant-wrapper">
            <div className="message-bubble assistant-bubble loading-bubble">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSend}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents... (Press Enter to send)"
          rows={1}
        />
        <button type="submit" className="chat-send-btn" disabled={!input.trim() || isLoading}>
          <svg viewBox="0 0 24 24" width="24" height="24">
            <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>
    </div>
  );
}
