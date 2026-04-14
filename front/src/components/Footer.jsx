import React from "react";
import "./Footer.css";

const Footer = () => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer className="footer" aria-label="Подвал сайта">
      <div className="footer-container">
        <div className="footer-top">
          <div className="footer-brand">
            <img src="./src/assets/Group 576.png" alt="VAMS" className="footer-logo" />
            <div className="footer-brand-copy">
              <p className="footer-title">VAMS Flowers</p>
              <p className="footer-text">
                Авторские букеты, внимательный сервис и доставка цветов для важных моментов.
              </p>
            </div>
          </div>

          <div className="footer-column">
            <p className="footer-heading">Контакты</p>
            <a className="footer-link" href="tel:+79991234567">
              +7 (999) 123-45-67
            </a>
            <a className="footer-link" href="mailto:hello@vamsflowers.ru">
              hello@vamsflowers.ru
            </a>
            <p className="footer-text">Москва, доставка ежедневно с 09:00 до 21:00</p>
          </div>

          <div className="footer-column footer-column--actions">
            <p className="footer-heading">Сервис</p>
            <p className="footer-badge">Поддержка клиентов 7 дней в неделю</p>
            <button type="button" className="footer-up" onClick={scrollToTop}>
              <img src="./src/assets/up.png" alt="" aria-hidden="true" />
              Наверх
            </button>
          </div>
        </div>

        <div className="footer-bottom">
          <p className="footer-copy">© {currentYear} VAMS Flowers. Все права защищены.</p>
          <p className="footer-copy">
            Сайт выполнен в учебном формате, но оформлен как полноценный сервис цветочной компании.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
