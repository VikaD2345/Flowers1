import {
  clearAdminToken,
  getAdminRefreshToken,
  getAdminToken,
  setAdminTokens,
  updateAdminAccessToken,
  updateAdminRefreshToken,
} from "../auth/adminAuthStorage";

const API_BASE =
  import.meta.env.VITE_API_URL?.toString().replace(/\/+$/, "") ??
  "http://127.0.0.1:8100";

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

let adminRefreshPromise = null;

async function createRequestError(res, payload) {
  const detail =
    payload?.detail ??
    payload?.message ??
    `Request failed with status ${res.status}`;
  const err = new Error(detail);
  err.status = res.status;
  err.payload = payload;
  return err;
}

async function doFetch(path, { method = "GET", body, token } = {}) {
  return fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function refreshAdminAccessToken() {
  if (adminRefreshPromise) {
    return adminRefreshPromise;
  }

  const refreshToken = getAdminRefreshToken();
  if (!refreshToken) {
    clearAdminToken();
    const err = new Error("Admin refresh token is missing");
    err.status = 401;
    throw err;
  }

  adminRefreshPromise = (async () => {
    const res = await doFetch("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      token: null,
    });
    const payload = await readJsonSafely(res);

    if (!res.ok) {
      clearAdminToken();
      throw await createRequestError(res, payload);
    }

    updateAdminAccessToken(payload?.access_token ?? "");
    updateAdminRefreshToken(payload?.refresh_token ?? "");
    return payload;
  })();

  try {
    return await adminRefreshPromise;
  } finally {
    adminRefreshPromise = null;
  }
}

export async function adminFetch(path, { method = "GET", body, token, requiresAuth = true, retry = true } = {}) {
  const authToken = token === null ? null : getAdminToken() ?? token;

  const res = await doFetch(path, { method, body, token: authToken });

  const payload = await readJsonSafely(res);

  if (res.status === 401 && requiresAuth && retry) {
    const refreshed = await refreshAdminAccessToken();
    const retryToken = refreshed?.access_token ?? getAdminToken();
    return adminFetch(path, { method, body, token: retryToken, requiresAuth, retry: false });
  }

  if (!res.ok) {
    if (res.status === 401) {
      clearAdminToken();
    }
    throw await createRequestError(res, payload);
  }

  return payload;
}

export async function adminLogin({ username, password }) {
  const payload = await adminFetch("/auth/login", {
    method: "POST",
    body: { username, password },
    token: null,
    requiresAuth: false,
  });
  if (payload?.access_token && payload?.refresh_token) {
    setAdminTokens({
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
    });
  }
  return payload;
}

export async function adminMe() {
  return adminFetch("/me");
}

export async function adminListOrders() {
  return adminFetch("/admin/orders");
}

export async function adminUpdateOrderStatus(orderId, status) {
  return adminFetch(`/admin/orders/${orderId}/status`, {
    method: "PATCH",
    body: { status },
  });
}

export async function adminDeleteOrder(orderId) {
  return adminFetch(`/admin/orders/${orderId}`, { method: "DELETE" });
}

export async function adminDeleteAllOrders() {
  return adminFetch("/admin/orders", { method: "DELETE" });
}

export async function adminListUsers() {
  return adminFetch("/admin/users");
}

export async function adminDeleteUser(userId) {
  return adminFetch(`/admin/users/${userId}`, { method: "DELETE" });
}

export async function adminDeleteAllUsers() {
  return adminFetch("/admin/users", { method: "DELETE" });
}

export async function adminListProducts() {
  return adminFetch("/flowers");
}

export async function adminCreateProduct({ name, description, category, price, image_url }) {
  return adminFetch("/admin/flowers", {
    method: "POST",
    body: {
      name,
      description,
      category,
      price: Number(price),
      image_url,
    },
  });
}

export async function adminUpdateProduct(id, { name, description, category, price, image_url }) {
  return adminFetch(`/admin/flowers/${id}`, {
    method: "PATCH",
    body: {
      ...(name !== undefined ? { name } : {}),
      ...(description !== undefined ? { description } : {}),
      ...(category !== undefined ? { category } : {}),
      ...(price !== undefined ? { price: Number(price) } : {}),
      ...(image_url !== undefined ? { image_url } : {}),
    },
  });
}

export async function adminDeleteProduct(id) {
  return adminFetch(`/admin/flowers/${id}`, { method: "DELETE" });
}

export async function adminDeleteAllProducts() {
  return adminFetch("/admin/flowers", { method: "DELETE" });
}

export async function adminListAudit({ limit = 100 } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return adminFetch(`/admin/audit?${params.toString()}`);
}

export async function adminForecastHealth() {
  return adminFetch("/forecast/health");
}

export async function adminForecastMetrics({ testDays = 30 } = {}) {
  const params = new URLSearchParams();
  params.set("test_days", String(testDays));
  return adminFetch(`/forecast/metrics?${params.toString()}`);
}

export async function adminForecastList({ days = 30, safetyStock = 0.15 } = {}) {
  const params = new URLSearchParams();
  params.set("days", String(days));
  params.set("safety_stock", String(safetyStock));
  return adminFetch(`/forecast?${params.toString()}`);
}

export async function adminForecastRetrain() {
  return adminFetch("/forecast/retrain", { method: "POST" });
}
