import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import "../admin.css";
import { clearAdminToken } from "../auth/adminAuthStorage";

const navItems = [
  { to: "/admin/dashboard", label: "Панель" },
  { to: "/admin/orders", label: "Заказы" },
  { to: "/admin/products", label: "Товары" },
  { to: "/admin/forecast", label: "Прогноз" },
  { to: "/admin/users", label: "Пользователи" },
  { to: "/admin/audit", label: "Аудит" },
];

export function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const title =
    navItems.find((item) => location.pathname.startsWith(item.to))?.label ??
    "Админка";

  return (
    <div className="adminShell">
      <aside className="adminSidebar">
        <div className="adminBrand">
          <div className="adminBrandMark" aria-hidden="true" />
          <div className="adminBrandText">
            <div className="adminBrandTitle">Админка Flowers</div>
            <div className="adminBrandSubtitle">Панель управления магазином</div>
          </div>
        </div>

        <nav className="adminNav" aria-label="Навигация админки">
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
            На сайт
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
              Выйти
            </button>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
