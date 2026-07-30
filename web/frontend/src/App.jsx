import { useState } from "react";
import "./App.css";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import LandingPage from "./components/LandingPage.jsx";
import Login from "./components/Login.jsx";
import Signup from "./components/Signup.jsx";
import Dashboard from "./components/Dashboard.jsx";
import ChatInterface from "./components/ChatInterface.jsx";

function LoggedInView() {
  const [tab, setTab] = useState("dashboard"); // "dashboard" | "chat"

  return (
    <div>
      <div style={{ display: "flex", gap: "1rem", padding: "1rem", borderBottom: "1px solid #ddd" }}>
        <button onClick={() => setTab("dashboard")}>Dashboard</button>
        <button onClick={() => setTab("chat")}>Chat</button>
      </div>

      {tab === "dashboard" && <Dashboard />}
      {tab === "chat" && <ChatInterface />}
    </div>
  );
}

function AppContent() {
  const [page, setPage] = useState("landing"); // "landing" | "login" | "signup"
  const { login, isLoggedIn } = useAuth();

  const handleLoginSuccess = (accessToken) => {
    login(accessToken);
  };

  if (isLoggedIn) {
    return <LoggedInView />;
  }

  if (page === "login") {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  if (page === "signup") {
    return <Signup />;
  }

  return <LandingPage onNavigate={setPage} />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;