export default function Button({ children, type="button", onClick, disabled, ariaLabel }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-disabled={disabled}
      style={{
        width: "100%",
        padding: "14px 16px",
        borderRadius: 8,
        border: "2px solid transparent",
        background: disabled ? "#374151" : "#2563eb",
        color: "#ffffff",
        fontWeight: 700,
        fontSize: "1rem",
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: disabled ? "none" : "0 4px 12px rgba(37, 99, 235, 0.4)",
        transition: "background-color 0.15s ease, box-shadow 0.15s ease",
        minHeight: "48px",
      }}
    >
      {children}
    </button>
  );
}
