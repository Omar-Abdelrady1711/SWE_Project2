import { useState } from "react";

export default function PasswordField({
  id,
  label = "Password",
  value,
  onChange,
  onBlur,
  placeholder,
  required,
  autoComplete = "current-password",
  error,
}) {
  const [visible, setVisible] = useState(false);
  const describedBy = error ? `${id}-error` : undefined;

  return (
    <div className="form-row">
      <label htmlFor={id}>{label}</label>
      <div style={{ position: "relative" }}>
        <input
          id={id}
          name={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          placeholder={placeholder}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          required={required}
          autoComplete={autoComplete}
          style={{ paddingRight: 52 }}
        />
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          aria-pressed={visible}
          aria-label={visible ? "Hide password" : "Show password"}
          style={{
            position: "absolute",
            right: 8,
            top: "50%",
            transform: "translateY(-50%)",
            height: 36,
            minWidth: 36,
            borderRadius: 6,
            border: "2px solid #4b5563",
            background: "#374151",
            color: "#ffffff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "1rem",
          }}
        >
          <span aria-hidden="true">{visible ? "🙈" : "👁️"}</span>
        </button>
      </div>
      {error && (
        <div id={`${id}-error`} className="error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
