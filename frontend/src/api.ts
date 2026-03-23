const API_BASE =
  typeof import.meta.env?.VITE_API_URL === "string" &&
  import.meta.env.VITE_API_URL.trim() !== ""
    ? import.meta.env.VITE_API_URL.replace(/\/$/, "")
    : "http://localhost:8000";

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}
