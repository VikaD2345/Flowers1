import "./CartPage.css";

const getItemsLabel = (count) => {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) {
    return "товар";
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return "товара";
  }
  return "товаров";
};

const CartPage = ({ items, onIncrease, onDecrease, onRemove, goToCatalog, onCheckout }) => {
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const totalCount = items.reduce((sum, item) => sum + item.qty, 0);
  const totalLabel = getItemsLabel(totalCount);

  return (
    <section className="cart-page" aria-label="Корзина">
      <div className="cart-header-row">
        <h1 className="cart-title">Корзина</h1>
        <p className="cart-subtitle">{totalCount} {totalLabel}</p>
      </div>

      <div className="cart-layout">
        <div className="cart-items">
          {items.length === 0 ? (
            <p className="cart-empty">Корзина пуста. Добавьте товары из каталога.</p>
          ) : (
            items.map((item) => (
              <article className="cart-item" key={item.id}>
                <img className="cart-item-image" src= "./src/assets/1.jpg" alt={item.title} />

                <div className="cart-item-info">
                  <p className="cart-item-price">{item.price * item.qty} ₽</p>
                  <h2 className="cart-item-title">{item.title}</h2>
                  <p className="cart-item-description">{item.description}</p>
                  <p className="cart-item-note">
                    Количество: {item.qty}
                    {item.isPending ? " • обновляем..." : ""}
                  </p>

                  <div className="cart-item-controls">
                    <div className="cart-qty-box">
                      <button
                        type="button"
                        onClick={() => onDecrease(item)}
                        aria-label="Уменьшить количество"
                        disabled={item.isPending}
                      >
                        -
                      </button>
                      <span>{item.qty}</span>
                      <button
                        type="button"
                        onClick={() => onIncrease(item)}
                        aria-label="Увеличить количество"
                        disabled={item.isPending}
                      >
                        +
                      </button>
                    </div>
                    <button
                      className="cart-remove"
                      type="button"
                      onClick={() => onRemove(item)}
                      aria-label="Удалить товар"
                      disabled={item.isPending}
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>

        <aside className="cart-sidebar">
          <button className="cart-continue" type="button" onClick={goToCatalog}>
            Продолжить покупки
          </button>
          <div className="cart-divider">
            <div className="cart-total">
              <p>{totalCount} {totalLabel}</p>
              <strong>{total} ₽</strong>
            </div>
            <button className="cart-pay" type="button" onClick={onCheckout} disabled={items.length === 0}>
              Оформить заказ
            </button>
          </div>
        </aside>
      </div>
    </section>
  );
};

export default CartPage;
