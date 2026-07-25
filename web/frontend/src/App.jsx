import { useState, useEffect } from "react";
import "./App.css";
import LandingPage from "./components/LandingPage.jsx";

function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("backend not reachable"));
  }, []);

  return <LandingPage onNavigate={(page) => console.log(page)} />;
}

export default App;