/**
 * http.js
 *
 * Minimal fetch helpers used by the service modules.
 */

import { getApiBaseUrl } from "./apiBase.js";

export async function postJson(path, body) {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "include",
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
    credentials: "include",
    body: formData
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return await res.json();
}

export async function getJson(path) {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "GET",
    credentials: "include",
    headers: { "Accept": "application/json" }
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return await res.json()
}
