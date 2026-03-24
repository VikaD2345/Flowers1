import { useEffect, useState } from "react";
import "./App.css";
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
import AuthPage from "./components/AuthPage";
import AccountPage from "./components/AccountPage";
import CheckoutPage from "./components/CheckoutPage";
import FlowerAssistant from "./components/FlowerAssistant";
import { getSessionUser, logoutLocalUser } from "./utils/authStorage";
import { createOrder, getOrdersByUserId } from "./utils/orderStorage";

export default function PublicApp() {
  const [currentPage, setCurrentPage] = useState("home");
  const [cartItems, setCartItems] = useState([]);
  const [authUser, setAuthUser] = useState(null);
  const [orders, setOrders] = useState([]);
  const [isAuthReady, setIsAuthReady] = useState(false);

  useEffect(() => {
    const sessionUser = getSessionUser();
    setAuthUser(sessionUser);
    setOrders(sessionUser ? getOrdersByUserId(sessionUser.id) : []);
    setIsAuthReady(true);
  }, []);

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

  const handleAuthSuccess = (user) => {
    setAuthUser(user);
    setOrders(getOrdersByUserId(user.id));
    setCurrentPage("account");
  };

  const handleLogout = () => {
    logoutLocalUser();
    setAuthUser(null);
    setOrders([]);
    setCurrentPage("home");
  };

  const handleProfileOpen = () => {
    setCurrentPage(authUser ? "account" : "auth");
  };

  const handleCheckoutOpen = () => {
    if (cartItems.length === 0) {
      return;
    }

    if (!authUser) {
      setCurrentPage("auth");
      return;
    }

    setCurrentPage("checkout");
  };

  const handleOrderSubmit = ({ address, paymentMethod }) => {
    const paymentLabel =
      paymentMethod === "card"
        ? "Банковская карта"
        : paymentMethod === "cash"
          ? "Наличными курьеру"
          : "СБП";

    const newOrder = createOrder({
      userId: authUser.id,
      items: cartItems,
      address,
      paymentMethod: paymentLabel,
    });

    setOrders((prev) => [newOrder, ...prev]);
    setCartItems([]);
    setCurrentPage("account");
  };

  if (!isAuthReady) {
    return null;
  }

  if (currentPage === "auth") {
    return (
      <>
        <AuthPage
          onBackHome={() => setCurrentPage("home")}
          onAuthSuccess={handleAuthSuccess}
        />
        <FlowerAssistant onAddToCart={addToCart} onOpenCatalog={goToCatalog} />
      </>
    );
  }

  if (currentPage === "account" && authUser) {
    return (
      <div className="page">
        <Header
          onNavigate={setCurrentPage}
          currentPage={currentPage}
          onOpenProfile={handleProfileOpen}
        />
        <AccountPage
          user={authUser}
          cartItems={cartItems}
          orders={orders}
          onBackHome={() => setCurrentPage("home")}
          onOpenCatalog={goToCatalog}
          onLogout={handleLogout}
        />
        <Footer />
        <FlowerAssistant onAddToCart={addToCart} onOpenCatalog={goToCatalog} />
      </div>
    );
  }

  if (currentPage === "checkout" && authUser) {
    return (
      <div className="page">
        <Header
          onNavigate={setCurrentPage}
          currentPage={currentPage}
          onOpenProfile={handleProfileOpen}
        />
        <CheckoutPage
          items={cartItems}
          onBackToCart={() => setCurrentPage("cart")}
          onSubmitOrder={handleOrderSubmit}
        />
        <Footer />
        <FlowerAssistant onAddToCart={addToCart} onOpenCatalog={goToCatalog} />
      </div>
    );
  }

  return (
    <div className="page">
      <Header
        onNavigate={setCurrentPage}
        currentPage={currentPage}
        onOpenProfile={handleProfileOpen}
      />
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
          goToCatalog={goToCatalog}
          onCheckout={handleCheckoutOpen}
        />
      )}
      <Footer />
      <FlowerAssistant onAddToCart={addToCart} onOpenCatalog={goToCatalog} />
    </div>
  );
}
