import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * ProtectedRoute - Wrapper component for routes that require authentication
 * Redirects to login if user is not authenticated
 */
export default function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, isAdmin } = useAuth();
  const location = useLocation();

  if (!isAuthenticated()) {
    // Redirect to login, preserving the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && !isAdmin()) {
    // User is authenticated but not an admin
    return (
      <div 
        role="alert" 
        aria-live="assertive"
        style={{
          padding: "2rem",
          textAlign: "center",
          color: "#721c24",
          backgroundColor: "#f8d7da",
          border: "1px solid #f5c6cb",
          borderRadius: "4px",
          margin: "2rem",
        }}
      >
        <h1>Access Denied</h1>
        <p>You need administrator privileges to access this page.</p>
      </div>
    );
  }

  return children;
}
