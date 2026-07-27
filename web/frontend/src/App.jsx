import { useState } from "react";
import "./App.css";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import LandingPage from "./components/LandingPage.jsx";
import Login from "./components/Login.jsx";
import Signup from "./components/Signup.jsx";
import Dashboard from "./components/Dashboard.jsx";
import UploadView from "./UploadView.jsx";

function AppContent() {
  const [page, setPage] = useState("landing"); // "landing" | "login" | "signup"
  const { login, isLoggedIn } = useAuth();

  const handleLoginSuccess = (accessToken) => {
    login(accessToken); 
  };

 
  if (isLoggedIn) {
    return <Dashboard />;
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