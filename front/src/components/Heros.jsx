import "../main.css";

const Main = () => {
  return (
    <main className="main">
        <div className="cover">
            <img className="cover-img" alt="Цветочная композиция" src="./src/assets/cover.png"></img>
            <div className="cover-text">
                <h1 className="cover-title">Доставка цветов</h1>
                <p>Цветы для любого случая <br/><strong>Доставляем самые свежие цветы <br/> в Москве</strong></p>
            </div>
        </div>
    </main> 
  );
}

export default Main;
