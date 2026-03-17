import "../main.css";

const Benefits = () => {
    return (
        <div className="why">
            <h2 className="why_title">Почему выбирают нас?</h2>
            <div className="why_conteiner">
                <div className="title_conteiner">
                    <div className="why_icoandtitle">
                        <h3 className="why_icoandtitle_title">Большой выбор</h3>
                        <img className="why_icon" alt="Иконка выбора" src="./src/assets/why_icon1.png" />
                    </div>
                    <p className="why_discription">У нас всегда свежие цветы и огромный ассортимент букетов на любой вкус и бюджет.</p>
                </div>
                <div className="title_conteiner">
                    <div className="why_icoandtitle">
                        <h3 className="why_icoandtitle_title">Быстрая доставка</h3>
                        <img className="why_icon" alt="Иконка доставки" src="./src/assets/why_icon2.png" />
                    </div>
                    <p className="why_discription">Доставляем цветы за максимально короткое время. Работаем с 8:00 до 22:00.</p>
                </div>
                <div className="title_conteiner">
                    <div className="why_icoandtitle">
                        <h3 className="why_icoandtitle_title">Онлайн-заказ</h3>
                        <img className="why_icon" alt="Иконка онлайн-заказа" src="./src/assets/why_icon3.png" />
                    </div>
                    <p className="why_discription">Заказывайте цветы онлайн 24/7. Наша команда всегда на связи и готова помочь.</p>
                </div>
            </div>
        </div>
    );
}

export default Benefits;