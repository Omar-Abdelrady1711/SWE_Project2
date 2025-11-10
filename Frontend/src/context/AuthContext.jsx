import { createContext, useContext, useMemo, useState } from "react";
import { getToken, setToken, clearToken } from "../utils/storage";
// import api from "../services/apiClient"; // use later

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTok] = useState(getToken());

  const login = async (username, password) => {
    // Later: const { data } = await api.post("/login", { username, password });
    // setToken(data.token); setTok(data.token);
    // return data;

    // For now, mock successful login path so UI can proceed:
    const fake = "mock.jwt.token";
    setToken(fake);
    setTok(fake);
    return { token: fake };
  };

  const logout = () => {
    clearToken();
    setTok(null);
  };

  const value = useMemo(() => ({ token, login, logout }), [token]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
