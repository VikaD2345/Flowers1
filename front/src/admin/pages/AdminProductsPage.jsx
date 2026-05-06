import { useEffect, useMemo, useState } from "react";
import "../admin.css";
import {
  adminCreateProduct,
  adminDeleteAllProducts,
  adminDeleteProduct,
  adminListProducts,
  adminUpdateProduct,
} from "../api/adminApi";

function normalizeProduct(p) {
  return {
    id: p.id,
    name: p.name ?? "",
    description: p.description ?? "",
    category: p.category ?? "Другое",
    price: Number(p.price ?? 0),
    image_url: p.image_url ?? "",
  };
}

export function AdminProductsPage() {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  const [draft, setDraft] = useState({
    name: "",
    description: "",
    category: "",
    price: "",
    image_url: "",
  });
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
        setError(err?.message ?? "Не удалось загрузить товары.");
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
    setDraft({ name: "", description: "", category: "", price: "", image_url: "" });
    setEditingId(null);
  };

  const startEdit = (p) => {
    setEditingId(p.id);
    setDraft({
      name: p.name,
      description: p.description,
      category: p.category,
      price: String(p.price),
      image_url: p.image_url,
    });
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const payload = {
      name: draft.name.trim(),
      description: draft.description.trim(),
      category: draft.category.trim(),
      price: Number(draft.price),
      image_url: draft.image_url.trim(),
    };
    if (!payload.name || !payload.category || !Number.isFinite(payload.price) || !payload.image_url) {
      setError("Заполните название, категорию, цену и URL изображения.");
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
      setError(err?.message ?? "Не удалось сохранить товар.");
    }
  };

  const onDelete = async (p) => {
    const ok = window.confirm(`Удалить товар "${p.name}"?`);
    if (!ok) return;
    setError(null);
    try {
      await adminDeleteProduct(p.id);
      setProducts((prev) => prev.filter((x) => x.id !== p.id));
      if (editingId === p.id) {
        resetDraft();
      }
    } catch (err) {
      setError(err?.message ?? "Не удалось удалить товар.");
    }
  };

  const onDeleteAll = async () => {
    const ok = window.confirm(
      "Удалить все товары? Это также очистит корзины и удалит все заказы, связанные с этими товарами."
    );
    if (!ok) return;

    setError(null);
    setIsDeletingAll(true);
    try {
      await adminDeleteAllProducts();
      setProducts([]);
      resetDraft();
    } catch (err) {
      setError(err?.message ?? "Не удалось удалить все товары.");
    } finally {
      setIsDeletingAll(false);
    }
  };

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol12">
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18 }}>Товары</div>
            <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
              Создавайте, редактируйте и удаляйте букеты.
            </div>
          </div>
          <button
            type="button"
            className="adminBtn adminBadgeDanger"
            onClick={onDeleteAll}
            disabled={isLoading || isDeletingAll}
          >
            {isDeletingAll ? "Удаляем..." : "Удалить все товары"}
          </button>
        </div>

        {error ? (
          <div style={{ marginTop: 12 }}>
            <span className="adminBadge adminBadgeDanger">Ошибка</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : null}

        <div className="adminGrid" style={{ marginTop: 14 }}>
          <div className="adminCard adminCol6">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>
              {editingId ? `Редактирование #${editingId}` : "Создать товар"}
            </div>
            <form onSubmit={onSubmit}>
              <div className="adminField">
                <label htmlFor="p-name">Название</label>
                <input
                  id="p-name"
                  value={draft.name}
                  onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                />
              </div>
              <div className="adminField">
                <label htmlFor="p-price">Цена</label>
                <input
                  id="p-price"
                  value={draft.price}
                  onChange={(e) => setDraft((d) => ({ ...d, price: e.target.value }))}
                  inputMode="decimal"
                />
              </div>
              <div className="adminField">
                <label htmlFor="p-category">Категория</label>
                <input
                  id="p-category"
                  value={draft.category}
                  onChange={(e) => setDraft((d) => ({ ...d, category: e.target.value }))}
                />
              </div>
              <div className="adminField">
                <label htmlFor="p-description">Описание</label>
                <textarea
                  id="p-description"
                  value={draft.description}
                  onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
                  rows={4}
                />
              </div>
              <div className="adminField">
                <label htmlFor="p-image">URL изображения</label>
                <input
                  id="p-image"
                  value={draft.image_url}
                  onChange={(e) => setDraft((d) => ({ ...d, image_url: e.target.value }))}
                />
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                <button type="submit" className="adminBtn adminBtnPrimary">
                  {editingId ? "Сохранить" : "Создать"}
                </button>
                <button type="button" className="adminBtn" onClick={resetDraft}>
                  Сбросить
                </button>
              </div>
            </form>
          </div>

          <div className="adminCard adminCol6">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Все товары</div>
            {isLoading ? (
              <div style={{ color: "rgba(255,255,255,0.72)" }}>Загрузка...</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="adminTable" aria-label="Таблица товаров">
                  <thead>
                    <tr>
                      <th style={{ width: 80 }}>ID</th>
                      <th>Название</th>
                      <th style={{ width: 120 }}>Цена</th>
                      <th style={{ width: 160 }}>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((p) => (
                      <tr key={p.id}>
                        <td>#{p.id}</td>
                        <td>
                          <div style={{ fontWeight: 700 }}>{p.name}</div>
                          <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>
                            {p.category}
                          </div>
                          <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>
                            {p.image_url}
                          </div>
                        </td>
                        <td>{p.price.toFixed(2)}</td>
                        <td>
                          <div style={{ display: "flex", gap: 8 }}>
                            <button type="button" className="adminBtn" onClick={() => startEdit(p)}>
                              Изменить
                            </button>
                            <button type="button" className="adminBtn" onClick={() => onDelete(p)}>
                              Удалить
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {sorted.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ color: "rgba(255,255,255,0.68)" }}>
                          Товары не найдены.
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
