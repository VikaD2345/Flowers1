import "../main.css";

const CartPage = ({ items, onIncrease, onDecrease, onRemove, onContinueShopping }) => {
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);

  return (
    <section className="cart-page" aria-label="Корзина">
      <div className="cart-header-row">
        <h1 className="cart-title">Корзина</h1>
        <button className="cart-continue" type="button" onClick={onContinueShopping}>
          Продолжить покупки
        </button>
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
                  <h2 className="cart-item-title">{item.title}</h2>
                  <p className="cart-item-price">{item.price * item.qty} ₽</p>
                  <p className="cart-item-description">{item.description}</p>
                </div>

                <div className="cart-item-controls">
                  <div className="cart-qty-box">
                    <button type="button" onClick={() => onDecrease(item.id)} aria-label="Уменьшить количество">
                      -
                    </button>
                    <span>{item.qty}</span>
                    <button type="button" onClick={() => onIncrease(item.id)} aria-label="Увеличить количество">
                      +
                    </button>
                  </div>
                  <button
                    className="cart-remove"
                    type="button"
                    onClick={() => onRemove(item.id)}
                    aria-label="Удалить товар"
                  >
                    🗑
                  </button>
                </div>
              </article>
            ))
          )}
        </div>

        <aside className="cart-sidebar">
          <div className="cart-total">
            <p>Сумма</p>
            <strong>{total} ₽</strong>
          </div>
          <button className="cart-pay" type="button">
            Оплатить
          </button>
        </aside>
      </div>
    </section>
  );
};

export default CartPage;
