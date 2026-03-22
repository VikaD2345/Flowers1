import { useState } from "react";
import "./Header.css";

function Header({ onNavigate, currentPage, onOpenProfile }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const closeMenu = () => setIsMenuOpen(false);
  const handleNavigate = (event, page) => {
    if (!onNavigate) {
      return;
    }
    event.preventDefault();
    onNavigate(page);
    closeMenu();
  };

  return (
    <header className="header">
      <div className="header__container">
        <img src = './src/assets/Group 576.png' className="logo"></img>

        <button
          type="button"
          className={`burger ${isMenuOpen ? "is-open" : ""}`}
          aria-label={isMenuOpen ? "Закрыть меню" : "Открыть меню"}
          aria-expanded={isMenuOpen}
          onClick={() => setIsMenuOpen((prev) => !prev)}
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        <nav className={`nav ${isMenuOpen ? "is-open" : ""}`}>
          <a href="#" onClick={(event) => handleNavigate(event, "home")} className={currentPage === "home" ? "is-active" : ""}>Главная</a>
          <a href="#" onClick={(event) => handleNavigate(event, "catalog")} className={currentPage === "catalog" ? "is-active" : ""}>Каталог</a>
          <a href="#" onClick={(event) => handleNavigate(event, "cart")} className={currentPage === "cart" ? "is-active" : ""}>Корзина</a>
        </nav>

        <div className="actions">
          <button
            type="button"
            className="profile"
            onClick={onOpenProfile}
            aria-label="Открыть страницу входа и регистрации"
          >
            <img src="./src/assets/Vector.png" alt="" className="profileImg"></img>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
