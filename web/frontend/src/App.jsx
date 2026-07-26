import { useState, useEffect } from "react";
import "./App.css";
import LandingPage from "./components/LandingPage.jsx";

function App() {
  const [token, setToken] = useState(null);

  return <LandingPage onNavigate={(page) => console.log(page)} />;
}

export default App;