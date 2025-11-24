import { createContext, useContext, useMemo, useState, useEffect } from "react";
import { getToken, setToken, clearToken, getUser, setUser } from "../utils/storage";
import api from "../services/apiClient";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTok] = useState(getToken());
  const [user, setUserState] = useState(getUser());
  const [loading, setLoading] = useState(false);

  // Listen for auth logout events from API interceptor
  useEffect(() => {
    const handleLogout = (event) => {
      if (event.detail?.reason === "unauthorized") {
        setTok(null);
        setUserState(null);
      }
    };
    
    window.addEventListener("auth:logout", handleLogout);
    return () => window.removeEventListener("auth:logout", handleLogout);
  }, []);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { username, password });
      
      setToken(data.access_token);
      setUser(data.user);
      setTok(data.access_token);
      setUserState(data.user);
      
      return data;
    } catch (error) {
      const message = error.response?.data?.detail || "Login failed. Please try again.";
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    clearToken();
    setTok(null);
    setUserState(null);
  };

  const value = useMemo(
    () => ({ 
      token, 
      user, 
      login, 
      logout, 
      loading,
      isAuthenticated: () => !!token && !!user,
      isAdmin: () => user?.role === "admin",
    }),
    [token, user, loading]
  );
  
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  return useContext(AuthCtx);
}
