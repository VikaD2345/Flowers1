import { useEffect, useRef, useState } from "react";
import "./buy_button.css";

const ACTIVE_DURATION_MS = 500;

const BuyButton = ({ onClick }) => {
  const [isAdded, setIsAdded] = useState(false);
  const resetTimeoutRef = useRef(null);

  useEffect(() => {
    return () => {
      if (resetTimeoutRef.current) {
        window.clearTimeout(resetTimeoutRef.current);
      }
    };
  }, []);

  const handleClick = async () => {
    const result = await onClick?.();

    if (result === false) {
      return;
    }

    if (resetTimeoutRef.current) {
      window.clearTimeout(resetTimeoutRef.current);
    }

    setIsAdded(true);
    resetTimeoutRef.current = window.setTimeout(() => {
      setIsAdded(false);
      resetTimeoutRef.current = null;
    }, ACTIVE_DURATION_MS);
  };

  return (
    <button
      className={`popular-card-button ${isAdded ? "is-added" : ""}`}
      onClick={handleClick}
      type="button"
    >
      {isAdded ? "В корзине" : "В корзину"}
    </button>
  );
};

export default BuyButton;
