import axios from "axios";

// import.meta.env.BASE_URL is "/" in dev, "/oncoplot/" in production subdirectory builds
const base = import.meta.env.BASE_URL.replace(/\/$/, "");

const api = axios.create({
  baseURL: `${base}/api`,
});

/** Prefix an API-returned path (e.g. "/api/render/xx/png") with the base path. */
export function withBase(path: string): string {
  return `${base}${path}`;
}

/** Inject the session ID header on every request when available. */
export function setSessionId(id: string) {
  api.defaults.headers.common["X-Session-Id"] = id;
}

export function clearSessionId() {
  delete api.defaults.headers.common["X-Session-Id"];
}

export default api;
