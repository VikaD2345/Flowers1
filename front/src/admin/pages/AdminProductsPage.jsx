import { useEffect, useMemo, useState } from "react";
import "../admin.css";
import {
  adminCreateProduct,
  adminDeleteProduct,
  adminListProducts,
  adminUpdateProduct,
} from "../api/adminApi";

function normalizeProduct(p) {
  return {
    id: p.id,
    name: p.name ?? "",
    price: Number(p.price ?? 0),
    image_url: p.image_url ?? "",
  };
}

export function AdminProductsPage() {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [draft, setDraft] = useState({ name: "", price: "", image_url: "" });
  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminListProducts()
      .then((rows) => {
        if (!isMounted) return;
        setProducts(Array.isArray(rows) ? rows.map(normalizeProduct) : []);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err?.message ?? "Failed to load products.");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const sorted = useMemo(() => {
    return [...products].sort((a, b) => a.id - b.id);
  }, [products]);

  const resetDraft = () => {
    setDraft({ name: "", price: "", image_url: "" });
    setEditingId(null);
  };

  const startEdit = (p) => {
    setEditingId(p.id);
    setDraft({ name: p.name, price: String(p.price), image_url: p.image_url });
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const payload = {
      name: draft.name.trim(),
      price: Number(draft.price),
      image_url: draft.image_url.trim(),
    };
    if (!payload.name || !Number.isFinite(payload.price) || !payload.image_url) {
      setError("Please fill name, price and image URL.");
      return;
    }

    try {
      if (editingId) {
        const updated = await adminUpdateProduct(editingId, payload);
        setProducts((prev) => prev.map((p) => (p.id === editingId ? normalizeProduct(updated) : p)));
      } else {
        const created = await adminCreateProduct(payload);
        setProducts((prev) => [...prev, normalizeProduct(created)]);
      }
      resetDraft();
    } catch (err) {
      setError(err?.message ?? "Failed to save product.");
    }
  };

  const onDelete = async (p) => {
    const ok = window.confirm(`Delete product "${p.name}"?`);
    if (!ok) return;
    setError(null);
    try {
      await adminDeleteProduct(p.id);
      setProducts((prev) => prev.filter((x) => x.id !== p.id));
      if (editingId === p.id) {
        resetDraft();
      }
    } catch (err) {
      setError(err?.message ?? "Failed to delete product.");
    }
  };

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol12">
        <div style={{ fontWeight: 800, fontSize: 18 }}>Products</div>
        <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
          Create, edit and delete bouquets.
        </div>

        {error ? (
          <div style={{ marginTop: 12 }}>
            <span className="adminBadge adminBadgeDanger">Error</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : null}

        <div className="adminGrid" style={{ marginTop: 14 }}>
          <div className="adminCard adminCol6">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>
              {editingId ? `Edit #${editingId}` : "Create product"}
            </div>
            <form onSubmit={onSubmit}>
              <div className="adminField">
                <label htmlFor="p-name">Name</label>
                <input
                  id="p-name"
                  value={draft.name}
                  onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                />
              </div>
              <div className="adminField">
                <label htmlFor="p-price">Price</label>
                <input
                  id="p-price"
                  value={draft.price}
                  onChange={(e) => setDraft((d) => ({ ...d, price: e.target.value }))}
                  inputMode="decimal"
                />
              </div>
              <div className="adminField">
                <label htmlFor="p-image">Image URL</label>
                <input
                  id="p-image"
                  value={draft.image_url}
                  onChange={(e) => setDraft((d) => ({ ...d, image_url: e.target.value }))}
                />
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                <button type="submit" className="adminBtn adminBtnPrimary">
                  {editingId ? "Save changes" : "Create"}
                </button>
                <button type="button" className="adminBtn" onClick={resetDraft}>
                  Reset
                </button>
              </div>
            </form>
          </div>

          <div className="adminCard adminCol6">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>All products</div>
            {isLoading ? (
              <div style={{ color: "rgba(255,255,255,0.72)" }}>Loading…</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="adminTable" aria-label="Products table">
                  <thead>
                    <tr>
                      <th style={{ width: 80 }}>ID</th>
                      <th>Name</th>
                      <th style={{ width: 120 }}>Price</th>
                      <th style={{ width: 160 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((p) => (
                      <tr key={p.id}>
                        <td>#{p.id}</td>
                        <td>
                          <div style={{ fontWeight: 700 }}>{p.name}</div>
                          <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>
                            {p.image_url}
                          </div>
                        </td>
                        <td>{p.price.toFixed(2)}</td>
                        <td>
                          <div style={{ display: "flex", gap: 8 }}>
                            <button type="button" className="adminBtn" onClick={() => startEdit(p)}>
                              Edit
                            </button>
                            <button type="button" className="adminBtn" onClick={() => onDelete(p)}>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {sorted.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ color: "rgba(255,255,255,0.68)" }}>
                          No products found.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

