import { useEffect, useState } from "react";
import "../admin.css";
import { adminDeleteAllUsers, adminDeleteUser, adminListUsers } from "../api/adminApi";

export function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminListUsers()
      .then((rows) => {
        if (!isMounted) return;
        setUsers(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err?.message ?? "Не удалось загрузить пользователей.");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const onDelete = async (user) => {
    const ok = window.confirm(`Удалить пользователя "${user.username}"?`);
    if (!ok) return;
    setError(null);
    try {
      await adminDeleteUser(user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err) {
      setError(err?.message ?? "Не удалось удалить пользователя.");
    }
  };

  const onDeleteAll = async () => {
    const ok = window.confirm(
      "Удалить всех пользователей, кроме текущего администратора? Их корзины и заказы тоже будут удалены."
    );
    if (!ok) return;

    setError(null);
    setIsDeletingAll(true);
    try {
      await adminDeleteAllUsers();
      const rows = await adminListUsers();
      setUsers(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err?.message ?? "Не удалось удалить всех пользователей.");
    } finally {
      setIsDeletingAll(false);
    }
  };

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol12">
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18 }}>Пользователи</div>
            <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
              Просматривайте аккаунты и управляйте ими.
            </div>
          </div>
          <button
            type="button"
            className="adminBtn adminBadgeDanger"
            onClick={onDeleteAll}
            disabled={isLoading || isDeletingAll}
          >
            {isDeletingAll ? "Удаляем..." : "Удалить всех пользователей"}
          </button>
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
            <table className="adminTable" aria-label="Таблица пользователей">
              <thead>
                <tr>
                  <th style={{ width: 90 }}>ID</th>
                  <th>Логин</th>
                  <th style={{ width: 140 }}>Роль</th>
                  <th style={{ width: 200 }}>Создан</th>
                  <th style={{ width: 160 }}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>#{u.id}</td>
                    <td>{u.username}</td>
                    <td>
                      <span className={`adminBadge ${u.role === "admin" ? "adminBadgeOk" : ""}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>{u.created_at ? new Date(u.created_at).toLocaleString() : "-"}</td>
                    <td>
                      <button
                        type="button"
                        className="adminBtn"
                        onClick={() => onDelete(u)}
                        disabled={u.role === "admin"}
                        title={u.role === "admin" ? "Нельзя удалить администратора" : "Удалить пользователя"}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ color: "rgba(255,255,255,0.68)" }}>
                      Пользователи не найдены.
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
