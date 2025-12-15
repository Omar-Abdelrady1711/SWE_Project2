export default function Button({ children, type="button", onClick, disabled, ariaLabel }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      style={{
        width: "100%",
        padding: "12px 14px",
        borderRadius: 10,
        border: "2px solid transparent",
        background: disabled ? "#1a2232" : "linear-gradient(180deg, #5b8cff, #3f6eef)",
        color: "white",
        fontWeight: 600,
        fontSize: "1rem",
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: disabled ? "none" : "0 8px 18px rgba(91,140,255,0.35)",
        transition: "box-shadow 0.2s ease, transform 0.1s ease",
      }}
      onFocus={(e) => {
        if (!disabled) {
          e.target.style.outline = "2px solid #8fb3ff";
          e.target.style.outlineOffset = "2px";
        }
      }}
      onBlur={(e) => {
        e.target.style.outline = "none";
      }}
    >
      {children}
    </button>
  );
}
