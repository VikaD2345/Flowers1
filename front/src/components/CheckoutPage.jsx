import { useState } from "react";
import "./CheckoutPage.css";

const paymentOptions = [
  { id: "card", label: "Картой курьеру" },
  { id: "cash", label: "Наличными курьеру" },
];

const formatPrice = (value) => `${Number(value).toLocaleString("ru-RU")} ₽`;

function CheckoutPage({ items, onBackToCart, onSubmitOrder }) {
  const [address, setAddress] = useState({
    street: "",
    house: "",
    entrance: "",
    apartment: "",
  });
  const [paymentMethod, setPaymentMethod] = useState(paymentOptions[0].id);
  const [error, setError] = useState("");

  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const totalCount = items.reduce((sum, item) => sum + item.qty, 0);

  const updateAddressField = (field, value) => {
    setAddress((prev) => ({ ...prev, [field]: value }));
  };

  const buildDeliveryAddress = () => {
    return `Улица ${address.street.trim()}, дом ${address.house.trim()}, подъезд ${address.entrance.trim()}, квартира ${address.apartment.trim()}`;
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    const street = address.street.trim();
    const house = address.house.trim();
    const entrance = address.entrance.trim();
    const apartment = address.apartment.trim();

    if (!street || !house || !entrance || !apartment) {
      setError("Заполни улицу, дом, подъезд и квартиру.");
      return;
    }

    if (street.length < 2) {
      setError("Укажи корректное название улицы.");
      return;
    }

    if (!/^[0-9A-Za-zА-Яа-я\-/]+$/.test(house)) {
      setError("Проверь номер дома.");
      return;
    }

    if (!/^[0-9]+$/.test(entrance)) {
      setError("Подъезд должен содержать только цифры.");
      return;
    }

    if (!/^[0-9A-Za-zА-Яа-я\-]+$/.test(apartment)) {
      setError("Проверь номер квартиры.");
      return;
    }

    setError("");
    onSubmitOrder({
      address: buildDeliveryAddress(),
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
              <div className="checkout-address-grid">
                <label className="checkout-field">
                  <span>Улица</span>
                  <input
                    className="checkout-input"
                    placeholder="Например, Ленина"
                    value={address.street}
                    onChange={(event) => updateAddressField("street", event.target.value)}
                  />
                </label>

                <label className="checkout-field">
                  <span>Дом</span>
                  <input
                    className="checkout-input"
                    placeholder="Например, 12А"
                    value={address.house}
                    onChange={(event) => updateAddressField("house", event.target.value)}
                  />
                </label>

                <label className="checkout-field">
                  <span>Подъезд</span>
                  <input
                    className="checkout-input"
                    placeholder="Например, 3"
                    value={address.entrance}
                    onChange={(event) => updateAddressField("entrance", event.target.value)}
                    inputMode="numeric"
                  />
                </label>

                <label className="checkout-field">
                  <span>Квартира</span>
                  <input
                    className="checkout-input"
                    placeholder="Например, 45"
                    value={address.apartment}
                    onChange={(event) => updateAddressField("apartment", event.target.value)}
                  />
                </label>
              </div>
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
                    <strong>{formatPrice(item.price * item.qty)}</strong>
                  </article>
                ))}
              </div>

              <div className="checkout-total-row">
                <span>{totalCount} товар{totalCount === 1 ? "" : totalCount < 5 ? "а" : "ов"}</span>
                <strong>{formatPrice(total)}</strong>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}

export default CheckoutPage;
