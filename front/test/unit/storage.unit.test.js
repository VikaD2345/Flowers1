import { describe, expect, it, vi } from "vitest";
import { getSessionUser, saveSession } from "../../src/utils/authStorage";
import { createOrder, getOrdersByUserId } from "../../src/utils/orderStorage";
import {
  clearAdminToken,
  getAdminRefreshToken,
  getAdminToken,
  setAdminTokens,
} from "../../src/admin/auth/adminAuthStorage";

describe("Юнит-тесты фронтенда", () => {
  it("сохраняет и возвращает текущего пользователя сессии", () => {
    const user = { id: 7, username: "alice" };

    saveSession({ user });

    expect(getSessionUser()).toEqual(user);
  });

  it("возвращает null и очищает хранилище при невалидном JSON сессии", () => {
    localStorage.setItem("flowersSessionUser", "{broken");

    expect(getSessionUser()).toBeNull();
    expect(localStorage.getItem("flowersSessionUser")).toBeNull();
  });

  it("создаёт заказ с правильно рассчитанной суммой и количеством товаров", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-19T10:00:00.000Z"));

    const order = createOrder({
      userId: "u-1",
      address: "Moscow",
      paymentMethod: "card",
      items: [
        { id: 1, title: "Rose", description: "Red", image: "/rose.jpg", price: 100, qty: 2 },
        { id: 2, title: "Tulip", description: "White", image: "/tulip.jpg", price: 50, qty: 3 },
      ],
    });

    expect(order.id).toBe("FL-1779184800000");
    expect(order.total).toBe(350);
    expect(order.itemCount).toBe(5);

    vi.useRealTimers();
  });

  it("фильтрует заказы по пользователю и сортирует их от новых к старым", () => {
    localStorage.setItem("flowersOrders", JSON.stringify([
      { id: "1", userId: "u-1", createdAt: "2026-05-18T10:00:00.000Z" },
      { id: "2", userId: "u-2", createdAt: "2026-05-19T10:00:00.000Z" },
      { id: "3", userId: "u-1", createdAt: "2026-05-19T12:00:00.000Z" },
    ]));

    expect(getOrdersByUserId("u-1").map((order) => order.id)).toEqual(["3", "1"]);
  });

  it("очищает оба токена администратора", () => {
    setAdminTokens({ accessToken: "access-1", refreshToken: "refresh-1" });

    clearAdminToken();

    expect(getAdminToken()).toBeNull();
    expect(getAdminRefreshToken()).toBeNull();
  });
});
