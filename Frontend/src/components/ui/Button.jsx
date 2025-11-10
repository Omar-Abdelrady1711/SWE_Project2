export default function Button({ children, type="button", onClick, disabled }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{
        width: "100%",
        padding: "12px 14px",
        borderRadius: 10,
        border: "1px solid #2a3347",
        background: disabled ? "#1a2232" : "linear-gradient(180deg, #5b8cff, #3f6eef)",
        color: "white",
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: disabled ? "none" : "0 8px 18px rgba(91,140,255,0.35)"
      }}
    >
      {children}
    </button>
  );
}
