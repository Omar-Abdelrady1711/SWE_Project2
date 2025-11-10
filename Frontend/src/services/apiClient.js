import axios from "axios";
import { getToken } from "../utils/storage";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL, // e.g., http://localhost:8000/api
  timeout: 15000,
});

// Attach token if present (we’ll use this later once backend auth exists)
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
