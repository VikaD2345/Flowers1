import { useState } from "react";
import "./CheckoutPage.css";

const paymentOptions = [
  { id: "card", label: "Банковская карта" },
  { id: "cash", label: "Наличными курьеру" },
  { id: "sbp", label: "СБП" },
];

function CheckoutPage({ items, onBackToCart, onSubmitOrder }) {
  const [address, setAddress] = useState("");
  const [paymentMethod, setPaymentMethod] = useState(paymentOptions[0].id);
  const [error, setError] = useState("");

  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const totalCount = items.reduce((sum, item) => sum + item.qty, 0);

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!address.trim()) {
      setError("Укажи адрес доставки.");
      return;
    }

    setError("");
    onSubmitOrder({
      address: address.trim(),
      paymentMethod,
    });
  };

  return (
    <section className="checkout-page" aria-label="Оформление заказа">
      <div className="checkout-page__inner">
        <div className="checkout-topbar">
          <div>
            <p className="account-page-label">Оформление заказа</p>
            <h1 className="checkout-title">Доставка и оплата</h1>
          </div>
          <button type="button" className="account-topbar-link" onClick={onBackToCart}>
            Вернуться в корзину
          </button>
        </div>

        <div className="checkout-layout">
          <form className="checkout-card" onSubmit={handleSubmit}>
            <div className="checkout-section">
              <h2 className="checkout-section-title">Адрес заказа</h2>
              <textarea
                className="checkout-textarea"
                placeholder="Город, улица, дом, подъезд, этаж, квартира"
                value={address}
                onChange={(event) => setAddress(event.target.value)}
              />
            </div>

            <div className="checkout-section">
              <h2 className="checkout-section-title">Способ оплаты</h2>
              <div className="checkout-payment-list">
                {paymentOptions.map((option) => (
                  <label key={option.id} className={`checkout-payment-option ${paymentMethod === option.id ? "is-active" : ""}`}>
                    <input
                      type="radio"
                      name="paymentMethod"
                      value={option.id}
                      checked={paymentMethod === option.id}
                      onChange={(event) => setPaymentMethod(event.target.value)}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {error ? <p className="register-message register-message-error">{error}</p> : null}

            <button type="submit" className="register-submit checkout-submit">
              Подтвердить заказ
            </button>
          </form>

          <aside className="checkout-summary">
            <div className="checkout-summary-card">
              <h2 className="checkout-section-title">Данные о заказе</h2>
              <div className="checkout-order-list">
                {items.map((item) => (
                  <article className="checkout-order-item" key={item.id}>
                    <img src={item.image} alt={item.title} className="checkout-order-image" />
                    <div className="checkout-order-info">
                      <h3>{item.title}</h3>
                      <p>{item.qty} шт.</p>
                    </div>
                    <strong>{item.price * item.qty} ₽</strong>
                  </article>
                ))}
              </div>

              <div className="checkout-total-row">
                <span>{totalCount} товар{totalCount === 1 ? "" : totalCount < 5 ? "а" : "ов"}</span>
                <strong>{total} ₽</strong>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}

export default CheckoutPage;
