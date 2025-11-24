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
    <main className="container" role="main" aria-labelledby="login-title">
      <h1 id="login-title">Welcome back</h1>
      <p className="p-muted">Sign in to ACME Trustworthy Register</p>

      {/* Development credentials info */}
      <div 
        style={{
          padding: "1rem",
          backgroundColor: "#e7f3ff",
          border: "1px solid #b3d9ff",
          borderRadius: "4px",
          marginBottom: "1.5rem",
          fontSize: "0.875rem",
        }}
        role="note"
      >
        <strong>Test Credentials:</strong>
        <ul style={{ margin: "0.5rem 0 0 1.5rem" }}>
          <li>Admin: <code>admin</code> / <code>admin123</code></li>
          <li>User: <code>user</code> / <code>user123</code></li>
        </ul>
      </div>

      <form onSubmit={onSubmit} noValidate>
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

          <div className="helper">
            Don’t have an account? <a href="#" aria-disabled="true">Ask an admin</a>
          </div>
        </div>
      </form>
    </main>
  );
}
