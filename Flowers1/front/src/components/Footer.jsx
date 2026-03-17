import React from 'react';
import "../main.css";

const Footer = () => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <footer className="footer" aria-label="Подвал сайта">
        <div className='footer-container'>
            <img src="./src/assets/Group 576.png" alt="logo" />
            <p className='footer-copy'>Данный сайт создан в целях обучения и не несёт никой комерчественной ценности.</p>
            <img className='up' src="./src/assets/up.png" alt="Наверх" onClick={scrollToTop}/>
        </div>
    </footer>
  );
};

export default Footer;
    
