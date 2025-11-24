const TOKEN_KEY = "acme_token";
const USER_KEY = "acme_user";

// Token management
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

// User info management
export const getUser = () => {
  const user = localStorage.getItem(USER_KEY);
  return user ? JSON.parse(user) : null;
};

export const setUser = (user) => {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const getUserRole = () => {
  const user = getUser();
  return user?.role || null;
};

export const isAdmin = () => {
  return getUserRole() === "admin";
};
