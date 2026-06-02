/** API base URL — empty in dev uses Vite proxy (same origin). */
export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_URL ?? "";
}

/** WebSocket base URL derived from API URL or current page origin. */
export function getWsBaseUrl(): string {
  const api = import.meta.env.VITE_API_URL;
  const httpBase = api && api.length > 0 ? api : window.location.origin;
  return httpBase.replace(/^http/, "ws");
}
