const API_BASE =
  import.meta.env.VITE_API_URL?.toString().replace(/\/+$/, "") ??
  "http://127.0.0.1:8000";

async function readJsonSafely(res) {
  const text = await res.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export async function apiFetch(path, { method = "GET", body, token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const payload = await readJsonSafely(res);

  if (!res.ok) {
    const detail =
      payload?.detail ??
      payload?.message ??
      `Request failed with status ${res.status}`;
    const err = new Error(detail);
    err.status = res.status;
    err.payload = payload;
    throw err;
  }

  return payload;
}
