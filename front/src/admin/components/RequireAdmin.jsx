import { useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { adminMe } from "../api/adminApi";
import { getAdminToken } from "../auth/adminAuthStorage";

export function RequireAdmin({ children }) {
  const location = useLocation();
  const token = getAdminToken();
  const [state, setState] = useState({ status: "checking", user: null, error: null });

  const canCheck = useMemo(() => Boolean(token), [token]);

  useEffect(() => {
    let isMounted = true;
    if (!canCheck) {
      setState({ status: "no_token", user: null, error: null });
      return;
    }

    setState({ status: "checking", user: null, error: null });
    adminMe()
      .then((user) => {
        if (!isMounted) return;
        setState({ status: "ok", user, error: null });
      })
      .catch((err) => {
        if (!isMounted) return;
        setState({ status: "error", user: null, error: err });
      });

    return () => {
      isMounted = false;
    };
  }, [canCheck]);

  if (!token || state.status === "no_token") {
    return <Navigate to="/admin/login" replace state={{ from: location }} />;
  }

  if (state.status === "checking") {
    return (
      <div style={{ padding: 24, color: "rgba(255,255,255,0.78)" }}>
        Checking access…
      </div>
    );
  }

  if (state.status === "error") {
    return <Navigate to="/admin/login" replace state={{ from: location }} />;
  }

  if (state.user?.role !== "admin") {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>Access denied</div>
        <div style={{ color: "rgba(255,255,255,0.72)", lineHeight: 1.5 }}>
          This account is not an administrator.
        </div>
      </div>
    );
  }

  return children;
}

