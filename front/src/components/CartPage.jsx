import "./CartPage.css";

const CartPage = ({ items, onIncrease, onDecrease, onRemove, goToCatalog, onCheckout }) => {
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const totalCount = items.reduce((sum, item) => sum + item.qty, 0);

  return (
    <section className="cart-page" aria-label="РљРѕСЂР·РёРЅР°">
      <div className="cart-header-row">
        <h1 className="cart-title">РљРѕСЂР·РёРЅР°</h1>
        <p className="cart-subtitle">{totalCount} С‚РѕРІР°СЂ{totalCount === 1 ? "" : totalCount < 5 ? "Р°" : "РѕРІ"}</p>
      </div>

      <div className="cart-layout">
        <div className="cart-items">
          {items.length === 0 ? (
            <p className="cart-empty">РљРѕСЂР·РёРЅР° РїСѓСЃС‚Р°. Р”РѕР±Р°РІСЊС‚Рµ С‚РѕРІР°СЂС‹ РёР· РєР°С‚Р°Р»РѕРіР°.</p>
          ) : (
            items.map((item) => (
              <article className="cart-item" key={item.id}>
                <img className="cart-item-image" src={item.image} alt={item.title} />

                <div className="cart-item-info">
                  <p className="cart-item-price">{item.price * item.qty} в‚Ѕ</p>
                  <h2 className="cart-item-title">{item.title}</h2>
                  <p className="cart-item-description">{item.description}</p>
                  <p className="cart-item-note">
                    РљРѕР»РёС‡РµСЃС‚РІРѕ: {item.qty}
                    {item.isPending ? " • обновляем..." : ""}
                  </p>

                  <div className="cart-item-controls">
                    <div className="cart-qty-box">
                      <button
                        type="button"
                        onClick={() => onDecrease(item)}
                        aria-label="РЈРјРµРЅСЊС€РёС‚СЊ РєРѕР»РёС‡РµСЃС‚РІРѕ"
                        disabled={item.isPending}
                      >
                        -
                      </button>
                      <span>{item.qty}</span>
                      <button
                        type="button"
                        onClick={() => onIncrease(item)}
                        aria-label="РЈРІРµР»РёС‡РёС‚СЊ РєРѕР»РёС‡РµСЃС‚РІРѕ"
                        disabled={item.isPending}
                      >
                        +
                      </button>
                    </div>
                    <button
                      className="cart-remove"
                      type="button"
                      onClick={() => onRemove(item)}
                      aria-label="РЈРґР°Р»РёС‚СЊ С‚РѕРІР°СЂ"
                      disabled={item.isPending}
                    >
                      РЈРґР°Р»РёС‚СЊ
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>

        <aside className="cart-sidebar">
          <button className="cart-continue" type="button" onClick={goToCatalog}>
            РџСЂРѕРґРѕР»Р¶РёС‚СЊ РїРѕРєСѓРїРєРё
          </button>
          <div className="cart-divider">
            <div className="cart-total">
              <p>{totalCount} С‚РѕРІР°СЂ{totalCount === 1 ? "" : totalCount < 5 ? "Р°" : "РѕРІ"}</p>
              <strong>{total} в‚Ѕ</strong>
            </div>
            <button className="cart-pay" type="button" onClick={onCheckout} disabled={items.length === 0}>
              РћС„РѕСЂРјРёС‚СЊ Р·Р°РєР°Р·
            </button>
          </div>
        </aside>
      </div>
    </section>
  );
};

export default CartPage;
