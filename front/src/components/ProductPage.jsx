import { useEffect } from "react";
import BuyButton from "./buy_button";
import "./ProductPage.css";

function ProductPage({ product, onClose, onAddToCart }) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  if (!product) {
    return null;
  }

  return (
    <div className="product-modal" role="dialog" aria-modal="true" aria-label={`Карточка товара ${product.title}`}>
      <button type="button" className="product-modal__backdrop" aria-label="Закрыть карточку товара" onClick={onClose} />
      <div className="product-modal__viewport">
        <article className="product-card-full">
          <button type="button" className="product-modal__close" aria-label="Закрыть" onClick={onClose}>
            <span aria-hidden="true" className="product-modal__close-icon">
              ×
            </span>
          </button>
          <div className="product-card-full__media">
            <img src={product.image} alt={product.title} className="product-card-full__image" />
          </div>

          <div className="product-card-full__content">
            <p className="product-card-full__eyebrow">{product.category}</p>
            <h1 className="product-card-full__title">{product.title}</h1>
            <p className="product-card-full__description">{product.description}</p>

            <div className="product-card-full__details">
              <div className="product-card-full__price">{product.price} ₽</div>
              <BuyButton onClick={() => onAddToCart(product)} />
            </div>
          </div>
        </article>
      </div>
    </div>
  );
}

export default ProductPage;
