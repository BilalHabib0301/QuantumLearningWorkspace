import AuthPage from "./AuthPage";

function Login({ onLoginSuccess }) {
  return <AuthPage initialMode="login" onLoginSuccess={onLoginSuccess} />;
}

export default Login;