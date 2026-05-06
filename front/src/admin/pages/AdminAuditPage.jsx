import { useEffect, useMemo, useState } from "react";
import "../admin.css";
import { adminListAudit } from "../api/adminApi";

function prettyJson(value) {
  if (value == null) return "-";
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
        setError(err?.message ?? "Не удалось загрузить журнал аудита.");
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
        <div style={{ fontWeight: 800, fontSize: 18 }}>Журнал аудита</div>
        <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
          История действий администратора: заказы, пользователи и товары.
        </div>

        {error ? (
          <div style={{ marginTop: 12 }}>
            <span className="adminBadge adminBadgeDanger">Ошибка</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : null}

        <div style={{ marginTop: 14, overflowX: "auto" }}>
          {isLoading ? (
            <div style={{ color: "rgba(255,255,255,0.72)", padding: 8 }}>
              Загрузка...
            </div>
          ) : (
            <table className="adminTable" aria-label="Таблица журнала аудита">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>ID</th>
                  <th style={{ width: 170 }}>Создан</th>
                  <th style={{ width: 140 }}>Кто</th>
                  <th style={{ width: 160 }}>Действие</th>
                  <th>Сущность</th>
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
                    <td>{r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
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
                      Событий аудита пока нет. Попробуйте изменить статус заказа или отредактировать товар.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="adminCard adminCol5">
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Подробности</div>
        {!selected ? (
          <div style={{ color: "rgba(255,255,255,0.68)", lineHeight: 1.5 }}>
            Выберите событие, чтобы увидеть состояние до и после изменения.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <div className="adminMetricLabel">До</div>
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
              <div className="adminMetricLabel">После</div>
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
          </div>
        )}
      </div>
    </div>
  );
}
