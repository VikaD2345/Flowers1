import "./CartPage.css";

const CartPage = ({ items, onIncrease, onDecrease, onRemove, goToCatalog, onCheckout }) => {
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const totalCount = items.reduce((sum, item) => sum + item.qty, 0);

  return (
    <section className="cart-page" aria-label="Корзина">

      <div className="cart-header-row">
        <h1 className="cart-title">Корзина</h1>
        <p className="cart-subtitle">{totalCount} товар{totalCount === 1 ? "" : totalCount < 5 ? "а" : "ов"}</p>
      </div>

      <div className="cart-layout">
        <div className="cart-items">
          {items.length === 0 ? (
            <p className="cart-empty">Корзина пуста. Добавьте товары из каталога.</p>
          ) : (
            items.map((item) => (
              <article className="cart-item" key={item.id}>
                <img className="cart-item-image" src={item.image} alt={item.title} />

                <div className="cart-item-info">
                  <p className="cart-item-price">{item.price * item.qty} ₽</p>
                  <h2 className="cart-item-title">{item.title}</h2>
                  <p className="cart-item-description">{item.description}</p>
                  <p className="cart-item-note">Количество: {item.qty}</p>

                  <div className="cart-item-controls">
                    <div className="cart-qty-box">
                      <button type="button" onClick={() => onDecrease(item)} aria-label="Уменьшить количество">
                        -
                      </button>
                      <span>{item.qty}</span>
                      <button type="button" onClick={() => onIncrease(item)} aria-label="Увеличить количество">
                        +
                      </button>
                    </div>
                    <button
                      className="cart-remove"
                      type="button"
                      onClick={() => onRemove(item)}
                      aria-label="Удалить товар"
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
              <p>{totalCount} товар{totalCount === 1 ? "" : totalCount < 5 ? "а" : "ов"}</p>
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
