import { useEffect, useState } from "react";
import "../admin.css";
import { adminDeleteUser, adminListUsers } from "../api/adminApi";

export function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

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
        setError(err?.message ?? "Failed to load users.");
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
    const ok = window.confirm(`Delete user "${user.username}"?`);
    if (!ok) return;
    try {
      await adminDeleteUser(user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err) {
      setError(err?.message ?? "Failed to delete user.");
    }
  };

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol12">
        <div style={{ fontWeight: 800, fontSize: 18 }}>Users</div>
        <div style={{ color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
          View and manage accounts.
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
            <table className="adminTable" aria-label="Users table">
              <thead>
                <tr>
                  <th style={{ width: 90 }}>ID</th>
                  <th>Username</th>
                  <th style={{ width: 140 }}>Role</th>
                  <th style={{ width: 200 }}>Created</th>
                  <th style={{ width: 160 }}>Actions</th>
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
                    <td>{u.created_at ? new Date(u.created_at).toLocaleString() : "—"}</td>
                    <td>
                      <button
                        type="button"
                        className="adminBtn"
                        onClick={() => onDelete(u)}
                        disabled={u.role === "admin"}
                        title={u.role === "admin" ? "Cannot delete admin" : "Delete user"}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ color: "rgba(255,255,255,0.68)" }}>
                      No users found.
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

