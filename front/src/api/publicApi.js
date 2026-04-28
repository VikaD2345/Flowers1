import localFlowerImage from "../assets/1.jpg";

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

async function request(path, { method = "GET", body, token } = {}) {
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

function resolveFlowerImage(imageUrl) {
  const normalized = typeof imageUrl === "string" ? imageUrl.trim() : "";

  if (!normalized) {
    return localFlowerImage;
  }

  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return localFlowerImage;
  }

  if (normalized.startsWith("./src/assets/")) {
    return localFlowerImage;
  }

  return normalized;
}

export function normalizeFlower(flower) {
  return {
    id: flower.id,
    productId: flower.id,
    title: flower.name ?? "",
    description: flower.description ?? "",
    category: flower.category ?? "Другое",
    price: Number(flower.price ?? 0),
    image: resolveFlowerImage(flower.image_url),
  };
}

function normalizeCartItem(item) {
  const flower = normalizeFlower(item.flower ?? {});
  return {
    ...flower,
    id: item.id,
    cartItemId: item.id,
    productId: flower.id,
    qty: Number(item.qty ?? 0),
  };
}

function normalizeOrderItem(item) {
  const flower = normalizeFlower(item.flower ?? {});
  return {
    id: flower.id,
    productId: flower.id,
    title: flower.title,
    description: flower.description,
    image: flower.image,
    price: Number(item.unit_price ?? flower.price ?? 0),
    qty: Number(item.qty ?? 0),
  };
}

export function normalizeOrder(order) {
  const items = Array.isArray(order.items) ? order.items.map(normalizeOrderItem) : [];
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const itemCount = items.reduce((sum, item) => sum + item.qty, 0);

  return {
    id: order.id,
    status: order.status ?? "new",
    createdAt: order.created_at,
    address: order.delivery_address ?? "",
    paymentMethod: order.payment_method ?? "",
    total,
    itemCount,
    items,
  };
}

export async function registerUser({ username, password }) {
  return request("/auth/register", {
    method: "POST",
    body: { username, password },
  });
}

export async function loginUser({ username, password }) {
  return request("/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

export async function fetchCurrentUser(token) {
  return request("/me", { token });
}

export async function fetchFlowers() {
  const payload = await request("/flowers");
  return Array.isArray(payload) ? payload.map(normalizeFlower) : [];
}

export async function fetchCart(token) {
  const payload = await request("/cart", { token });
  return Array.isArray(payload) ? payload.map(normalizeCartItem) : [];
}

export async function addCartItem(token, flowerId, qty = 1) {
  const payload = await request("/cart/items", {
    method: "POST",
    token,
    body: { flower_id: flowerId, qty },
  });
  return normalizeCartItem(payload);
}

export async function updateCartItem(token, itemId, qty) {
  const payload = await request(`/cart/items/${itemId}`, {
    method: "PATCH",
    token,
    body: { qty },
  });
  return normalizeCartItem(payload);
}

export async function deleteCartItem(token, itemId) {
  return request(`/cart/items/${itemId}`, {
    method: "DELETE",
    token,
  });
}

export async function fetchOrders(token) {
  const payload = await request("/me/orders", { token });
  return Array.isArray(payload) ? payload.map(normalizeOrder) : [];
}

export async function createOrder(token, { address, paymentMethod }) {
  const payload = await request("/orders/from-cart", {
    method: "POST",
    token,
    body: {
      address,
      payment_method: paymentMethod,
    },
  });
  return normalizeOrder(payload);
}

export async function askFlowerAssistant(messages, limit = 3) {
  const payload = await request("/assistant/chat", {
    method: "POST",
    body: { messages, limit },
  });

  return {
    text: payload?.reply ?? "",
    suggestions: Array.isArray(payload?.products) ? payload.products.map(normalizeFlower) : [],
    criteria: payload?.criteria ?? null,
    needsClarification: Boolean(payload?.needs_clarification),
    source: payload?.source ?? "",
  };
}

function parseSseEvent(rawEvent) {
  const dataLines = rawEvent
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());

  if (dataLines.length === 0) {
    return null;
  }

  try {
    return JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }
}

export async function streamFlowerAssistant(messages, { limit = 3, onMeta, onChunk, onDone } = {}) {
  const res = await fetch(`${API_BASE}/assistant/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ messages, limit }),
  });

  if (!res.ok) {
    const payload = await readJsonSafely(res);
    const detail =
      payload?.detail ??
      payload?.message ??
      `Request failed with status ${res.status}`;
    const err = new Error(detail);
    err.status = res.status;
    err.payload = payload;
    throw err;
  }

  if (!res.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload = null;

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const rawEvent of parts) {
      const payload = parseSseEvent(rawEvent);
      if (!payload) {
        continue;
      }

      if (payload.type === "meta") {
        onMeta?.({
          criteria: payload.criteria ?? null,
          suggestions: Array.isArray(payload.products) ? payload.products.map(normalizeFlower) : [],
          needsClarification: Boolean(payload.needs_clarification),
          source: payload.source ?? "",
        });
        continue;
      }

      if (payload.type === "delta") {
        onChunk?.(payload.delta ?? "");
        continue;
      }

      if (payload.type === "done") {
        finalPayload = {
          text: payload.reply ?? "",
          suggestions: Array.isArray(payload.products) ? payload.products.map(normalizeFlower) : [],
          criteria: payload.criteria ?? null,
          needsClarification: Boolean(payload.needs_clarification),
          source: payload.source ?? "",
        };
        onDone?.(finalPayload);
      }
    }

    if (done) {
      break;
    }
  }

  return finalPayload;
}
