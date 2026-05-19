import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../src/App";
import AuthPage from "../../src/components/AuthPage";
import { RequireAdmin } from "../../src/admin/components/RequireAdmin";
import { AdminDashboardPage } from "../../src/admin/pages/AdminDashboardPage";

const { loginUser, fetchCurrentUser, registerUser, saveSession } = vi.hoisted(() => ({
  loginUser: vi.fn(),
  fetchCurrentUser: vi.fn(),
  registerUser: vi.fn(),
  saveSession: vi.fn(),
}));

const { adminListOrders, adminMe, getAdminToken } = vi.hoisted(() => ({
  adminListOrders: vi.fn(),
  adminMe: vi.fn(),
  getAdminToken: vi.fn(),
}));

vi.mock("../../src/api/publicApi", () => ({
  fetchCurrentUser,
  loginUser,
  registerUser,
}));

vi.mock("../../src/utils/authStorage", () => ({
  saveSession,
}));

vi.mock("../../src/admin/api/adminApi", () => ({
  adminListOrders,
  adminMe,
}));

vi.mock("../../src/admin/auth/adminAuthStorage", () => ({
  getAdminToken,
}));

vi.mock("../../src/PublicApp", () => ({
  default: () => <div>Public app page</div>,
}));

vi.mock("../../src/admin/AdminApp", () => ({
  AdminApp: () => <div>Admin app page</div>,
}));

describe("Автотесты фронтенда", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("показывает ошибку валидации при отправке пустой формы регистрации", async () => {
    const user = userEvent.setup();
    render(<AuthPage initialMode="register" />);

    await user.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    expect(await screen.findByText("Заполни все поля перед регистрацией.")).toBeInTheDocument();
  });

  it("выполняет вход пользователя и вызывает callback успешной авторизации", async () => {
    const user = userEvent.setup();
    const onAuthSuccess = vi.fn();
    loginUser.mockResolvedValue({ access_token: "token-1" });
    fetchCurrentUser.mockResolvedValue({ id: 5, username: "anna" });

    render(<AuthPage initialMode="login" onAuthSuccess={onAuthSuccess} />);

    const inputs = document.querySelectorAll('section[aria-hidden="false"] input');
    await user.type(inputs[0], "anna");
    await user.type(inputs[1], "secret");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(loginUser).toHaveBeenCalledWith({ username: "anna", password: "secret" });
      expect(fetchCurrentUser).toHaveBeenCalledWith("token-1");
      expect(saveSession).toHaveBeenCalledWith({ user: { id: 5, username: "anna" } });
      expect(onAuthSuccess).toHaveBeenCalledWith({ id: 5, username: "anna" }, "token-1");
    });
  });

  it("отображает метрики админ-панели, рассчитанные по загруженным заказам", async () => {
    adminListOrders.mockResolvedValue([
      {
        status: "new",
        items: [
          { unit_price: 100, qty: 2 },
          { unit_price: 50, qty: 1 },
        ],
      },
      {
        status: "done",
        items: [{ unit_price: 200, qty: 1 }],
      },
    ]);

    render(<AdminDashboardPage />);

    expect(await screen.findByText("450.00")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("225.00")).toBeInTheDocument();
  });

  it("перенаправляет на страницу входа, если нет токена администратора", () => {
    getAdminToken.mockReturnValue(null);

    render(
      <MemoryRouter initialEntries={["/admin/dashboard"]}>
        <Routes>
          <Route
            path="/admin/dashboard"
            element={
              <RequireAdmin>
                <div>Secret dashboard</div>
              </RequireAdmin>
            }
          />
          <Route path="/admin/login" element={<div>Admin login page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Admin login page")).toBeInTheDocument();
  });

  it("перенаправляет неизвестные маршруты на публичную часть приложения", () => {
    render(
      <MemoryRouter initialEntries={["/unknown"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByText("Public app page")).toBeInTheDocument();
  });
});
