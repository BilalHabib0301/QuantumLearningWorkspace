import { useState } from "react";
import "./App.css";
import LandingPage from "./components/LandingPage.jsx";
import Login from "./components/Login.jsx";
import Signup from "./components/Signup.jsx";

function App() {
  const [page, setPage] = useState("landing"); // "landing" | "login" | "signup"
  const [token, setToken] = useState(null);

  const handleLoginSuccess = (accessToken) => {
    setToken(accessToken);
    // Dashboard page isn't merged yet — for now we just store the token
    console.log("Logged in, token:", accessToken);
  };

  if (page === "login") {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  if (page === "signup") {
    return <Signup />;
  }

  return <LandingPage onNavigate={setPage} />;
}

export default App;