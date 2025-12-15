import { useState } from "react";
import InputField from "../components/form/InputField.jsx";
import PasswordField from "../components/form/PasswordField.jsx";
import Button from "../components/ui/Button.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useNavigate, useLocation } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", password: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitErr, setSubmitErr] = useState("");

  const validate = () => {
    const e = {};
    if (!form.username.trim()) e.username = "Username is required.";
    if (!form.password) e.password = "Password is required.";
    if (form.password && form.password.length < 6) e.password = "Password must be at least 6 characters.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onChange = (field) => (ev) => {
    setForm((f) => ({ ...f, [field]: ev.target.value }));
  };

  const onSubmit = async (ev) => {
    ev.preventDefault();
    setSubmitErr("");
    if (!validate()) return;

    setSubmitting(true);
    try {
      await login(form.username.trim(), form.password);
      // Redirect to the page they tried to access, or dashboard
      const from = location.state?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    } catch (err) {
      const message = err.message || "Invalid credentials or server error.";
      setSubmitErr(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main id="main-content" className="container" role="main" aria-labelledby="login-title">
      <h1 id="login-title">Welcome back</h1>
      <p className="p-muted">Sign in to ACME Trustworthy Registry</p>

      {/* Development credentials info */}
      <div 
        style={{
          padding: "1rem",
          backgroundColor: "#1e3a5f",
          border: "2px solid #60a5fa",
          borderRadius: "8px",
          marginBottom: "1.5rem",
          fontSize: "1rem",
          color: "#ffffff",
        }}
        role="note"
        aria-label="Test credentials for development"
      >
        <strong style={{ color: "#93c5fd" }}>Test Credentials:</strong>
        <ul style={{ margin: "0.5rem 0 0 0", paddingLeft: "1.5rem" }}>
          <li style={{ marginBottom: "0.25rem" }}>Admin: <code style={{ backgroundColor: "#374151", padding: "2px 8px", borderRadius: "4px", color: "#ffffff" }}>admin</code> / <code style={{ backgroundColor: "#374151", padding: "2px 8px", borderRadius: "4px", color: "#ffffff" }}>admin123</code></li>
          <li>User: <code style={{ backgroundColor: "#374151", padding: "2px 8px", borderRadius: "4px", color: "#ffffff" }}>user</code> / <code style={{ backgroundColor: "#374151", padding: "2px 8px", borderRadius: "4px", color: "#ffffff" }}>user123</code></li>
        </ul>
      </div>

      <form onSubmit={onSubmit} noValidate aria-describedby="form-instructions">
        <p id="form-instructions" className="sr-only">Enter your username and password to sign in.</p>
        <InputField
          id="username"
          label="Username"
          value={form.username}
          onChange={onChange("username")}
          placeholder="e.g., username123"
          required
          autoComplete="username"
          error={errors.username}
        />

        <PasswordField
          id="password"
          label="Password"
          value={form.password}
          onChange={onChange("password")}
          placeholder="Your password"
          required
          autoComplete="current-password"
          error={errors.password}
        />

        <div className="actions">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </Button>

          {submitErr && (
            <div className="error" role="alert" aria-live="polite">
              {submitErr}
            </div>
          )}

          <p className="helper">
            Don't have an account? Contact your administrator to request access.
          </p>
        </div>
      </form>
    </main>
  );
}
