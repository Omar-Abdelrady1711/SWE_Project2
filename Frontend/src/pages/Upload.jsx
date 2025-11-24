import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/apiClient";
import "./Upload.css";

export default function Upload() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    type: "model",
    url: "",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const errs = {};
    
    if (!form.url.trim()) {
      errs.url = "URL is required";
    } else {
      try {
        const url = new URL(form.url);
        if (!["http:", "https:"].includes(url.protocol)) {
          errs.url = "URL must use HTTP or HTTPS protocol";
        }
      } catch {
        errs.url = "Please enter a valid URL";
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError("");
    setSuccess(false);

    if (!validate()) return;

    setSubmitting(true);
    try {
      await api.post(`/artifact/${form.type}`, { url: form.url });
      setSuccess(true);
      setForm({ type: "model", url: "" });
      
      // Navigate to dashboard after short delay
      setTimeout(() => {
        navigate("/dashboard");
      }, 2000);
    } catch (err) {
      const message = err.response?.data?.detail || "Upload failed. Please try again.";
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <header className="upload-header">
          <button
            onClick={() => navigate("/dashboard")}
            className="back-button"
            aria-label="Back to dashboard"
          >
            ← Back
          </button>
          <h1 id="upload-title">Upload Artifact</h1>
        </header>

        <main role="main" aria-labelledby="upload-title">
          {success && (
            <div
              className="success-message"
              role="alert"
              aria-live="polite"
            >
              <strong>Success!</strong> Artifact uploaded successfully. Redirecting...
            </div>
          )}

          {submitError && (
            <div
              className="error-message"
              role="alert"
              aria-live="assertive"
            >
              <strong>Error:</strong> {submitError}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="upload-form">
            <div className="form-group">
              <label htmlFor="artifact-type">
                Artifact Type <span aria-label="required">*</span>
              </label>
              <select
                id="artifact-type"
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                required
                className="form-select"
              >
                <option value="model">Model</option>
                <option value="dataset">Dataset</option>
                <option value="code">Code</option>
              </select>
              <small className="help-text">
                Select the type of artifact you're uploading
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="artifact-url">
                Artifact URL <span aria-label="required">*</span>
              </label>
              <input
                id="artifact-url"
                type="url"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                placeholder="https://example.com/artifact"
                required
                className={`form-input ${errors.url ? "error" : ""}`}
                aria-invalid={!!errors.url}
                aria-describedby={errors.url ? "url-error" : "url-help"}
              />
              {errors.url && (
                <div id="url-error" className="field-error" role="alert">
                  {errors.url}
                </div>
              )}
              <small id="url-help" className="help-text">
                Enter the full URL to your artifact (e.g., HuggingFace model URL)
              </small>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                disabled={submitting}
                className="btn btn-primary btn-large"
              >
                {submitting ? (
                  <>
                    <span className="spinner-sm" aria-hidden="true"></span>
                    Uploading...
                  </>
                ) : (
                  <>
                    <span aria-hidden="true">⬆️</span>
                    Upload Artifact
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="btn btn-secondary"
                disabled={submitting}
              >
                Cancel
              </button>
            </div>
          </form>
        </main>
      </div>
    </div>
  );
}
