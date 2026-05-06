import "./AboutUs.css";

function AboutUs() {
  return (
    <section className="about-us" aria-label="О нас">
      <div className="about-us__shell">
        <div className="about-us__lead">
          <p className="about-us__eyebrow">О нас</p>
          <h2 className="about-us__title">Создаём букеты, которые говорят за вас</h2>
          <p className="about-us__text">
            Мы собираем цветочные композиции для тех моментов, когда важно передать чувство точно:
            нежность, благодарность, любовь или тёплую поддержку. Для нас букет это не просто
            покупка, а маленькая история, собранная вручную.
          </p>
        </div>

        <div className="about-us__grid">
          <article className="about-us__card">
            <span className="about-us__metric">5+</span>
            <h3 className="about-us__card-title">лет заботы о каждом заказе</h3>
            <p className="about-us__card-text">
              От подбора свежих цветов до финальной упаковки мы продумываем каждую деталь.
            </p>
          </article>

          <article className="about-us__card about-us__card--accent">
            <h3 className="about-us__card-title">Свежесть и аккуратная сборка</h3>
            <p className="about-us__card-text">
              Работаем только со свежими цветами и собираем букеты так, чтобы они радовали дольше
              и выглядели как на витрине.
            </p>
          </article>

          <article className="about-us__card">
            <h3 className="about-us__card-title">Доставка в нужный момент</h3>
            <p className="about-us__card-text">
              Помогаем поздравить вовремя: бережно привозим букет и следим, чтобы он приехал в
              идеальном состоянии.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}

export default AboutUs;
