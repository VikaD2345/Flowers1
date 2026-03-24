import { useEffect, useMemo, useState } from "react";
import "../admin.css";
import { adminListOrders, adminUpdateOrderStatus } from "../api/adminApi";

const statusMeta = {
  new: { label: "new", badge: "adminBadgeWarn" },
  delivering: { label: "delivering", badge: "" },
  done: { label: "done", badge: "adminBadgeOk" },
  canceled: { label: "canceled", badge: "adminBadgeDanger" },
};

function calcOrderTotal(order) {
  if (!order?.items?.length) return 0;
  return order.items.reduce((sum, it) => sum + Number(it.unit_price) * Number(it.qty), 0);
}

export function AdminOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminListOrders()
      .then((rows) => {
        if (!isMounted) return;
        setOrders(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err?.message ?? "Failed to load orders.");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (statusFilter === "all") return orders;
    return orders.filter((o) => o.status === statusFilter);
  }, [orders, statusFilter]);

  const onChangeStatus = async (orderId, nextStatus) => {
    try {
      const updated = await adminUpdateOrderStatus(orderId, nextStatus);
      setOrders((prev) => prev.map((o) => (o.id === orderId ? updated : o)));
    } catch (err) {
      setError(err?.message ?? "Failed to update order.");
    }
  };

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol12">
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18 }}>Orders</div>
            <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
              Manage order statuses and review items.
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div className="adminField" style={{ marginTop: 0, minWidth: 180 }}>
              <label htmlFor="statusFilter">Status</label>
              <select
                id="statusFilter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All</option>
                <option value="new">new</option>
                <option value="delivering">delivering</option>
                <option value="done">done</option>
                <option value="canceled">canceled</option>
              </select>
            </div>
          </div>
        </div>

        {error ? (
          <div style={{ marginTop: 12 }}>
            <span className="adminBadge adminBadgeDanger">Error</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : null}

        <div style={{ marginTop: 14, overflowX: "auto" }}>
          {isLoading ? (
            <div style={{ color: "rgba(255,255,255,0.72)", padding: 8 }}>
              Loading…
            </div>
          ) : (
            <table className="adminTable" aria-label="Orders table">
              <thead>
                <tr>
                  <th style={{ width: 90 }}>ID</th>
                  <th style={{ width: 170 }}>Created</th>
                  <th style={{ width: 130 }}>Status</th>
                  <th style={{ width: 120 }}>Total</th>
                  <th>Items</th>
                  <th style={{ width: 220 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((o) => {
                  const meta = statusMeta[o.status] ?? { label: o.status, badge: "" };
                  const total = calcOrderTotal(o);
                  return (
                    <tr key={o.id}>
                      <td>#{o.id}</td>
                      <td>{o.created_at ? new Date(o.created_at).toLocaleString() : "—"}</td>
                      <td>
                        <span className={`adminBadge ${meta.badge}`}>{meta.label}</span>
                      </td>
                      <td>{total.toFixed(2)}</td>
                      <td>
                        <div style={{ display: "grid", gap: 6 }}>
                          {(o.items ?? []).map((it, idx) => (
                            <div key={`${o.id}-${idx}`} style={{ color: "rgba(255,255,255,0.78)" }}>
                              {it.flower?.name ?? "—"} × {it.qty}{" "}
                              <span style={{ color: "rgba(255,255,255,0.55)" }}>
                                @ {Number(it.unit_price).toFixed(2)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          <select
                            aria-label={`Update status for order ${o.id}`}
                            value={o.status}
                            onChange={(e) => onChangeStatus(o.id, e.target.value)}
                          >
                            <option value="new">new</option>
                            <option value="delivering">delivering</option>
                            <option value="done">done</option>
                            <option value="canceled">canceled</option>
                          </select>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ color: "rgba(255,255,255,0.68)" }}>
                      No orders found.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

