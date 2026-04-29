/**
 * apiBase.js
 *
 * Centralizes the base URL used by frontend service modules.
 */

export function getApiBaseUrl() {
  return import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000";
}
