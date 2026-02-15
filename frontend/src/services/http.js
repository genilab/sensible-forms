/**
 * http.js
 *
 * Minimal fetch helpers used by the example service modules.
 */

// Example Code:
import { getApiBaseUrl } from "./apiBase.js";

export async function postJson(path, body) {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return await res.json();
}

export async function postMultipart(path, formData) {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return await res.json();
}
