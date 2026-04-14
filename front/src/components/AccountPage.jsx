import { useState } from "react";
import "./AccountPage.css";

const orderStatusLabels = {
  new: "СОЗДАН",
  delivering: "ДОСТАВЛЯЕТСЯ",
  done: "ЗАВЕРШЕН",
  canceled: "ОТМЕНЕН",
};

function AccountPage({ user, cartItems, orders, onBackHome, onOpenCatalog, onLogout }) {
  const [activeTab, setActiveTab] = useState("profile");
  const totalItems = cartItems.reduce((sum, item) => sum + item.qty, 0);
  const totalPrice = cartItems.reduce((sum, item) => sum + item.price * item.qty, 0);
  const usernameInitial = user?.username?.slice(0, 1).toUpperCase() ?? "U";

  return (
    <section className="account-page" aria-label="Личный кабинет">
      <div className="account-page__inner">
        <div className="account-topbar">
          <p className="account-page-label">Профиль</p>
          <button type="button" className="account-topbar-link" onClick={onBackHome}>
            На главную
          </button>
        </div>

        <div className="account-card">
          <div className="account-tabs">
            <button
              type="button"
              className={`account-tab ${activeTab === "profile" ? "is-active" : ""}`}
              onClick={() => setActiveTab("profile")}
            >
              Профиль
            </button>
            <button
              type="button"
              className={`account-tab ${activeTab === "orders" ? "is-active" : ""}`}
              onClick={() => setActiveTab("orders")}
            >
              Заказы
            </button>
          </div>

          {activeTab === "profile" ? (
            <>
          <div className="account-hero">
            <div className="account-avatar">{usernameInitial}</div>
            <div className="account-heading">
              <p className="account-kicker">Личный кабинет</p>
              <h1 className="account-name">{user.username}</h1>
              <p className="account-role">Статус: {user.role === "admin" ? "Администратор" : "Покупатель"}</p>
            </div>
          </div>

          <div className="account-grid">
            <article className="account-stat">
              <span>Имя пользователя</span>
              <strong>{user.username}</strong>
            </article>
            <article className="account-stat">
              <span>Роль</span>
              <strong>{user.role}</strong>
            </article>
            <article className="account-stat">
              <span>Товаров в корзине</span>
              <strong>{totalItems}</strong>
            </article>
            <article className="account-stat">
              <span>Сумма корзины</span>
              <strong>{totalPrice} ₽</strong>
            </article>
          </div>

          <div className="account-actions">
            <button type="button" className="register-submit account-primary-action" onClick={onOpenCatalog}>
              Перейти в каталог
            </button>
            <button type="button" className="account-secondary-action" onClick={onBackHome}>
              На главную
            </button>
            <button type="button" className="register-login-link account-logout-link" onClick={onLogout}>
              Выйти из аккаунта
            </button>
          </div>
            </>
          ) : (
            <div className="account-orders">
              <div className="account-orders-head">
                <h2 className="checkout-section-title">Мои заказы</h2>
              </div>

              {orders.length === 0 ? (
                <div className="account-orders-empty">
                  <p>У тебя пока нет оформленных заказов.</p>
                  <button type="button" className="register-submit account-primary-action" onClick={onOpenCatalog}>
                    Перейти в каталог
                  </button>
                </div>
              ) : (
                <div className="account-orders-list">
                  {orders.map((order) => (
                    <article className="account-order-card" key={order.id}>
                      <div className="account-order-meta">
                        <div>
                          <p className="account-order-id">{order.id}</p>
                          <p className="account-order-date">
                            {new Date(order.createdAt).toLocaleString("ru-RU")}
                          </p>
                        </div>
                        <span className="account-order-status">{orderStatusLabels[order.status] ?? order.status}</span>
                      </div>

                      <div className="account-order-details">
                        <p><strong>Адрес:</strong> {order.address}</p>
                        <p><strong>Оплата:</strong> {order.paymentMethod}</p>
                        <p><strong>Состав:</strong> {order.itemCount} шт. на сумму {order.total} ₽</p>
                      </div>

                      <div className="account-order-items">
                        {order.items.map((item) => (
                          <div className="account-order-item" key={`${order.id}-${item.id}`}>
                            <img src=" ./src/assets/1.jpg" alt={item.title} className="account-order-item-image" />
                            <div>
                              <h3>{item.title}</h3>
                              <p>{item.qty} шт. x {item.price} ₽</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default AccountPage;
