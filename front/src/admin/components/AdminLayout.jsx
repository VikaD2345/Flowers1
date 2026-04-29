import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import "../admin.css";
import { clearAdminToken } from "../auth/adminAuthStorage";

const navItems = [
  { to: "/admin/dashboard", label: "Dashboard" },
  { to: "/admin/orders", label: "Orders" },
  { to: "/admin/products", label: "Products" },
  { to: "/admin/forecast", label: "Forecast" },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/audit", label: "Audit" },
];

export function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const title =
    navItems.find((item) => location.pathname.startsWith(item.to))?.label ??
    "Admin";

  return (
    <div className="adminShell">
      <aside className="adminSidebar">
        <div className="adminBrand">
          <div className="adminBrandMark" aria-hidden="true" />
          <div className="adminBrandText">
            <div className="adminBrandTitle">Flowers Admin</div>
            <div className="adminBrandSubtitle">Demo-ready console</div>
          </div>
        </div>

        <nav className="adminNav" aria-label="Admin navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "adminNavActive" : "")}
            >
              <span>{item.label}</span>
              <span aria-hidden="true">-&gt;</span>
            </NavLink>
          ))}
        </nav>

        <div style={{ marginTop: 16 }}>
          <button
            type="button"
            className="adminBtn"
            onClick={() => navigate("/")}
          >
            Back to site
          </button>
        </div>
      </aside>

      <main className="adminMain">
        <header className="adminTopbar">
          <div className="adminTopbarTitle">{title}</div>
          <div className="adminTopbarRight">
            <button
              type="button"
              className="adminBtn"
              onClick={() => {
                clearAdminToken();
                navigate("/admin/login");
              }}
            >
              Logout
            </button>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
