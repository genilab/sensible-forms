/**
 * http.js
 *
 * Minimal fetch helpers used by the service modules.
 */

import { getApiBaseUrl } from "./apiBase.js";

function getAuthHeaders() {
  const token = localStorage.getItem("refresh_token");
  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
}

export async function postJson(path, body) {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders()
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
    headers: {
      ...getAuthHeaders()
    },
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
    headers: {
      "Accept": "application/json",
      ...getAuthHeaders()
    }
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return await res.json()
}
