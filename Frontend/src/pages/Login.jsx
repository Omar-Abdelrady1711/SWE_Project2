import { useState } from "react";
import InputField from "../components/form/InputField.jsx";
import PasswordField from "../components/form/PasswordField.jsx";
import Button from "../components/ui/Button.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
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
      // later will call the real API via AuthContext -> apiClient
      await login(form.username.trim(), form.password);
      navigate("/", { replace: true });
    } catch (err) {
      setSubmitErr("Invalid credentials or server error.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="container" role="main" aria-labelledby="login-title">
      <h1 id="login-title">Welcome back</h1>
      <p className="p-muted">Sign in to ACME Trustworthy Register</p>

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
