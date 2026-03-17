
import "../main.css";
import React from "react";

const Location = () => {
  return (
    <section className="location" aria-label="Контакты и адрес">
      <div className="location-info">
        <img
          className="location-icon"
          src="./src/assets/location-icon.svg"
          alt="Иконка локации"
        />
        <h2 className="location-title">Где мы находимся</h2>
        <p className="location-address">
          Новая Москва, ул. Москвитина д. 3к2
          <br />
          Время работы c 9:00 до 21:00
        </p>
      </div>
    </section>
  );
};

export default Location;
