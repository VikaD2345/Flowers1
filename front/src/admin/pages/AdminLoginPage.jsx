import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../admin.css";
import { adminLogin, adminMe } from "../api/adminApi";
import { setAdminToken } from "../auth/adminAuthStorage";

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const tokenOut = await adminLogin({ username: username.trim(), password });
      if (!tokenOut?.access_token) {
        throw new Error("Login failed: missing token.");
      }
      setAdminToken(tokenOut.access_token);

      const me = await adminMe();
      if (me?.role !== "admin") {
        throw new Error("Этот аккаунт не является администратором.");
      }

      navigate("/admin/dashboard");
    } catch (err) {
      setError(err?.message ?? "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="adminLoginWrap">
      <div className="adminLoginCard">
        <div style={{ fontWeight: 800, fontSize: 20 }}>Admin sign in</div>
        <div className="adminHelp">
          Для демо используется bootstrap админ в backend: <b>admin/admin</b>
        </div>
        {error ? (
          <div style={{ marginTop: 10, color: "rgba(255,255,255,0.92)" }}>
            <span className="adminBadge adminBadgeDanger">Ошибка</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : null}

        <form onSubmit={onSubmit}>
          <div className="adminField">
            <label htmlFor="admin-username">Username</label>
            <input
              id="admin-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div className="adminField">
            <label htmlFor="admin-password">Password</label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
            <button type="submit" className="adminBtn adminBtnPrimary">
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
            <button
              type="button"
              className="adminBtn"
              onClick={() => navigate("/")}
              disabled={isSubmitting}
            >
              Back to site
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

