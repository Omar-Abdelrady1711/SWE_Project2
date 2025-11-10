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
          style={{ paddingRight: 44 }}
        />
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          aria-pressed={visible}
          aria-label={visible ? "Hide password" : "Show password"}
          style={{
            position: "absolute",
            right: 6,
            top: 6,
            height: 32,
            minWidth: 32,
            borderRadius: 8,
            border: "1px solid #2a3347",
            background: "#0f1320",
            color: "#e7ebf3",
            cursor: "pointer"
          }}
        >
          {visible ? "🙈" : "👁️"}
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
