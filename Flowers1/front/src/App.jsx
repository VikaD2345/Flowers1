import { useState } from "react";
import "./main.css";
import Header from "./components/Header";
import Main1 from "./components/Heros";
import Popular from "./components/Popular";
import Benefits from "./components/Benefits";
import FAQ from "./components/FAQ";
import Gallery from "./components/Gallery";
import Location from "./components/Location";
import Footer from "./components/Footer";
import CartPage from "./components/CartPage";
import CatalogPage from "./components/CatalogPage";
import RegisterPage from "./components/RegisterPage";

export default function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [cartItems, setCartItems] = useState([]);

  const addToCart = (product) => {
    setCartItems((prev) => {
      const existingItem = prev.find((item) => item.id === product.id);
      if (existingItem) {
        return prev.map((item) =>
          item.id === product.id ? { ...item, qty: item.qty + 1 } : item
        );
      }
      return [...prev, { ...product, qty: 1 }];
    });
    setCurrentPage("cart");
  };

  const goToCatalog = () => {
    setCurrentPage("catalog");
  };

  const increaseQty = (id) => {
    setCartItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, qty: item.qty + 1 } : item))
    );
  };

  const decreaseQty = (id) => {
    setCartItems((prev) =>
      prev
        .map((item) => (item.id === id ? { ...item, qty: item.qty - 1 } : item))
        .filter((item) => item.qty > 0)
    );
  };

  const removeFromCart = (id) => {
    setCartItems((prev) => prev.filter((item) => item.id !== id));
  };

  if (currentPage === "register") {
    return <RegisterPage onOpenLogin={() => setCurrentPage("home")} />;
  }

  return (
    <div className="page">
      <Header onNavigate={setCurrentPage} currentPage={currentPage} />
      {currentPage === "catalog" ? (
        <CatalogPage onAddToCart={addToCart} />
      ) : currentPage === "home" ? (
        <>
          <Main1 />
          <Popular onAddToCart={addToCart} goToCatalog={goToCatalog} />
          <Benefits />
          <FAQ />
          <Gallery />
          <Location />
        </>
      ) : (
        <CartPage
          items={cartItems}
          onIncrease={increaseQty}
          onDecrease={decreaseQty}
          onRemove={removeFromCart}
          onContinueShopping={() => setCurrentPage("home")}
        />
      )}
      <Footer />
    </div>
  );
}
