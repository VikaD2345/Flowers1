import { useEffect, useMemo, useRef, useState } from "react";
import products from "../product.json";
import "../main.css";
import BuyButton from "./buy_button";

const PAGE_SIZE = 6;

const CatalogPage = ({ onAddToCart }) => {
  const [activeCategory, setActiveCategory] = useState("Все");
  const [query, setQuery] = useState("");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const filterRef = useRef(null);

  const categories = useMemo(() => {
    const values = new Set(products.map((item) => item.category));
    return ["Все", ...values];
  }, []);

  const filteredProducts = useMemo(() => {
    return products.filter((item) => {
      const categoryMatch = activeCategory === "Все" || item.category === activeCategory;
      const searchMatch = item.title.toLowerCase().includes(query.toLowerCase());
      return categoryMatch && searchMatch;
    });
  }, [activeCategory, query]);

  const visibleProducts = filteredProducts.slice(0, visibleCount);
  const canShowMore = visibleCount < filteredProducts.length;

  const handleCategoryClick = (category) => {
    setActiveCategory(category);
    setVisibleCount(PAGE_SIZE);
    setIsFilterOpen(false);
  };

  const handleSearchChange = (event) => {
    setQuery(event.target.value);
    setVisibleCount(PAGE_SIZE);
  };

  useEffect(() => {
    if (!isFilterOpen) {
      return undefined;
    }

    const handleClickOutside = (event) => {
      if (!filterRef.current) {
        return;
      }
      if (!filterRef.current.contains(event.target)) {
        setIsFilterOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isFilterOpen]);

  return (
    <section className="catalog-page" aria-label="Каталог">
      <div className="catalog-main">
        <h1 className="catalog-title">Каталог</h1>

        <div className="catalog-toolbar" ref={filterRef}>
          <button
            type="button"
            className="catalog-filter-toggle"
            aria-expanded={isFilterOpen}
            aria-label="Открыть фильтр"
            onClick={() => setIsFilterOpen((prev) => !prev)}
          >
            Фильтр
          </button>

          {isFilterOpen ? (
            <aside className="catalog-filter-dropdown" aria-label="Фильтр">
              <input
                type="search"
                className="catalog-filter-search"
                placeholder="Поиск"
                value={query}
                onChange={handleSearchChange}
              />

              <ul className="catalog-filter-list">
                {categories.map((category) => (
                  <li key={category}>
                    <button
                      type="button"
                      className={`catalog-filter-item ${activeCategory === category ? "is-active" : ""}`}
                      onClick={() => handleCategoryClick(category)}
                    >
                      {category}
                    </button>
                  </li>
                ))}
              </ul>
            </aside>
          ) : null}
        </div>

        <div className="catalog-grid">
          {visibleProducts.map((product) => (
            <article key={product.id} className="catalog-card">
              <img className="catalog-card-image" src={product.image} alt={product.title} />
              <div className="catalog-card-footer">
                <div className="catalog-card-meta">
                  <h3 className="catalog-card-title">{product.title}</h3>
                  <p className="catalog-card-description">{product.description}</p>
                  <p className="catalog-card-price">{product.price} ₽</p>
                </div>
                <BuyButton onClick={() => onAddToCart(product)} />
              </div>
            </article>
          ))}
        </div>

        {visibleProducts.length === 0 ? (
          <p className="catalog-empty">Ничего не найдено по текущему фильтру.</p>
        ) : null}

        {canShowMore ? (
          <button type="button" className="catalog-more" onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}>
            Смотреть ещё
          </button>
        ) : null}
      </div>
    </section>
  );
};

export default CatalogPage;
