import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

/** Inject the session ID header on every request when available. */
export function setSessionId(id: string) {
  api.defaults.headers.common["X-Session-Id"] = id;
}

export function clearSessionId() {
  delete api.defaults.headers.common["X-Session-Id"];
}

export default api;
