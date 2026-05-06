import React from "react";
import "./Location.css";

const Location = () => {
  return (
    <section className="location" aria-label="Контакты и адрес">
      <div className="location-shell">
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

        <div className="location-map">
          <a
            className="location-map__meta"
            href="https://yandex.com/maps/213/moscow/?utm_medium=mapframe&utm_source=maps"
            target="_blank"
            rel="noreferrer"
          >
            Москва
          </a>

          <iframe
            title="Карта с адресом магазина"
            src="https://yandex.com/map-widget/v1/?ll=37.358642%2C55.600038&mode=search&ol=geo&ouri=ymapsbm1%3A%2F%2Fgeo%3Fdata%3DCgoxNTg5NTc4NzU1EsoB0KDQvtGB0YHQuNGPLCDQnNC-0YHQutCy0LAsINCd0L7QstC-0LzQvtGB0LrQvtCy0YHQutC40Lkg0LDQtNC80LjQvdC40YHRgtGA0LDRgtC40LLQvdGL0Lkg0L7QutGA0YPQsywg0KTQuNC70LjQvNC-0L3QutC-0LLRgdC60LjQuSDRgNCw0LnQvtC9LCDQnNC-0YHQutC-0LLRgdC60LjQuSwg0YPQu9C40YbQsCDQnNC-0YHQutCy0LjRgtC40L3QsCwgM9C6MiIKDUBvFUIVcWZeQg%2C%2C&z=17.19"
            loading="lazy"
            allowFullScreen
          />
        </div>
      </div>
    </section>
  );
};

export default Location;
