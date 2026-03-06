import { useState } from "react";
import "../main.css";

const faqItems = [
  {
    question: "Можно ли заказать доставку цветов на сегодня?",
    answer: "Да, вы можете оформить заказ на доставку в день заказа. При наличии свободных курьеров доставка возможна в течение нескольких часов.",
  },
  {
    question: "Сколько стоит доставка цветов?",
    answer: "Стоимость доставки зависит от района Москвы и времени доставки. Точную стоимость вы увидите при оформлении заказа.",
  },
  {
    question: "Вы доставляете цветы в воскресенье?",
    answer: "Да, мы работаем без выходных и доставляем цветы в воскресенье.",
  },
  {
    question: "Сколько времени занимает доставка?",
    answer: "Обычно доставка занимает от 1 до 3 часов после подтверждения заказа.",
  },
  {
    question: "Можно ли забрать заказ из магазина?",
    answer: "Да, вы можете оформить самовывоз из нашего магазина в удобное для вас время.",
  },
  {
    question: "Можно ли заказать доставку на завтра?",
    answer: "Да, вы можете оформить предварительный заказ на любую удобную дату, включая завтра.",
  },
  {
    question: "В какие районы Москвы вы доставляете?",
    answer: "Мы доставляем цветы по всей Москве.",
  },
  {
    question: "Можно ли собрать свой букет?",
    answer: "Нет, мы занимается доставкой готовых букетов.",
  },
];

const FAQ = () => {
  const [openIndex, setOpenIndex] = useState(null);

  const toggleItem = (index) => {
    setOpenIndex((prev) => (prev === index ? null : index));
  };

  return (
    <section className="faq" aria-label="Часто задаваемые вопросы">
      <h2 className="faq-title">Часто задаваемые вопросы</h2>

      <div className="faq-list">
        {faqItems.map((item, index) => {
          const isOpen = openIndex === index;

          return (
            <article className="faq-item" key={item.question}>
              <button
                className="faq-question"
                onClick={() => toggleItem(index)}
                type="button"
                aria-expanded={isOpen}
              >
                <span>{item.question}</span>
                <span className="faq-icon">{isOpen ? "-" : "+"}</span>
              </button>

              <div
                className={`faq-answer-wrap ${isOpen ? "is-open" : ""}`}
                aria-hidden={!isOpen}
              >
                <p className="faq-answer">{item.answer}</p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
};

export default FAQ;
