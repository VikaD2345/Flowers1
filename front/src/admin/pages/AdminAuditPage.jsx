import { useEffect, useMemo, useState } from "react";
import "../admin.css";
import { adminListAudit } from "../api/adminApi";

function prettyJson(value) {
  if (value == null) return "—";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function AdminAuditPage() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminListAudit({ limit: 200 })
      .then((data) => {
        if (!isMounted) return;
        setRows(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err?.message ?? "Failed to load audit log.");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const selected = useMemo(() => {
    return rows.find((r) => r.id === selectedId) ?? null;
  }, [rows, selectedId]);

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol7">
        <div style={{ fontWeight: 800, fontSize: 18 }}>Audit log</div>
        <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
          Admin actions history (orders/users/products).
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
            <table className="adminTable" aria-label="Audit log table">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>ID</th>
                  <th style={{ width: 170 }}>Created</th>
                  <th style={{ width: 140 }}>Actor</th>
                  <th style={{ width: 160 }}>Action</th>
                  <th>Entity</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    style={{
                      cursor: "pointer",
                      background:
                        selectedId === r.id ? "rgba(139, 92, 246, 0.12)" : "transparent",
                    }}
                  >
                    <td>#{r.id}</td>
                    <td>{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                    <td>{r.actor_username}</td>
                    <td>
                      <span className="adminBadge">{r.action}</span>
                    </td>
                    <td>
                      {r.entity}
                      {r.entity_id != null ? (
                        <span style={{ color: "rgba(255,255,255,0.55)" }}> #{r.entity_id}</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ color: "rgba(255,255,255,0.68)" }}>
                      No audit events yet. Try changing an order status or editing a product.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="adminCard adminCol5">
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Details</div>
        {!selected ? (
          <div style={{ color: "rgba(255,255,255,0.68)", lineHeight: 1.5 }}>
            Select an event to see before/after payload.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <div className="adminMetricLabel">Before</div>
              <pre
                style={{
                  margin: 0,
                  marginTop: 6,
                  padding: 10,
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(0,0,0,0.18)",
                  overflowX: "auto",
                }}
              >
                {prettyJson(selected.before)}
              </pre>
            </div>
            <div>
              <div className="adminMetricLabel">After</div>
              <pre
                style={{
                  margin: 0,
                  marginTop: 6,
                  padding: 10,
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(0,0,0,0.18)",
                  overflowX: "auto",
                }}
              >
                {prettyJson(selected.after)}
              </pre>
            </div>
            <div>
              <div className="adminMetricLabel">Meta</div>
              <pre
                style={{
                  margin: 0,
                  marginTop: 6,
                  padding: 10,
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(0,0,0,0.18)",
                  overflowX: "auto",
                }}
              >
                {prettyJson(selected.meta)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

