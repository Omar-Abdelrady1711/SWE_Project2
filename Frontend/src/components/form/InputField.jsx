export default function InputField({
  id,
  label,
  type = "text",
  value,
  onChange,
  onBlur,
  placeholder,
  required,
  autoComplete,
  error,
}) {
  const describedBy = error ? `${id}-error` : undefined;

  return (
    <div className="form-row">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        placeholder={placeholder}
        aria-invalid={!!error}
        aria-describedby={describedBy}
        required={required}
        autoComplete={autoComplete}
      />
      {error && (
        <div id={`${id}-error`} className="error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
