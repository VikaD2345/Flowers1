import { clearAdminToken, getAdminToken } from "../auth/adminAuthStorage";

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

export async function adminFetch(path, { method = "GET", body, token } = {}) {
  const authToken = token ?? getAdminToken();

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const payload = await readJsonSafely(res);

  if (!res.ok) {
    if (res.status === 401) {
      clearAdminToken();
    }
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

export async function adminLogin({ username, password }) {
  return adminFetch("/auth/login", { method: "POST", body: { username, password }, token: null });
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

export async function adminListUsers() {
  return adminFetch("/admin/users");
}

export async function adminDeleteUser(userId) {
  return adminFetch(`/admin/users/${userId}`, { method: "DELETE" });
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

export async function adminListAudit({ limit = 100 } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return adminFetch(`/admin/audit?${params.toString()}`);
}
