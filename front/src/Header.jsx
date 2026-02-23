import "./main.css";

function Header() {
  return (
    <header className="header">
      <div className="header__container">
        <img src = 'src/assets/Group 576.png' className="logo"></img>

        <nav className="nav">
          <a href="#">Главная</a>
          <a href="#">Каталог</a>
          <a href="#">О нас</a>
          <a href="#">Корзина</a>
        </nav>

        <div className="actions">
          <input type="text" placeholder="Поиск" />
          <div className="profile"><img src="src/assets/Vector.png" alt="" className="profileImg"></img></div>
        </div>
      </div>
    </header>
  );
}

export default Header;
