import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* placeholder routes for later */}
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
