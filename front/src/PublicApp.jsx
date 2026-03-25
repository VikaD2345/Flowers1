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
import {
  addCartItem,
  createOrder,
  fetchCart,
  fetchCurrentUser,
  fetchFlowers,
  fetchOrders,
  updateCartItem,
  deleteCartItem,
} from "./api/publicApi";
import { getAccessToken, getSessionUser, logoutLocalUser, saveSession } from "./utils/authStorage";

const PAYMENT_LABELS = {
  card: "Банковская карта",
  cash: "Наличными курьеру",
  sbp: "СБП",
};

export default function PublicApp() {
  const [currentPage, setCurrentPage] = useState("home");
  const [products, setProducts] = useState([]);
  const [cartItems, setCartItems] = useState([]);
  const [authUser, setAuthUser] = useState(null);
  const [orders, setOrders] = useState([]);
  const [accessToken, setAccessToken] = useState(null);
  const [catalogError, setCatalogError] = useState("");
  const [isCatalogLoading, setIsCatalogLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [isAppReady, setIsAppReady] = useState(false);

  useEffect(() => {
    let isMounted = true;

    fetchFlowers()
      .then((items) => {
        if (!isMounted) {
          return;
        }
        setProducts(items);
        setCatalogError("");
      })
      .catch((error) => {
        if (!isMounted) {
          return;
        }
        setCatalogError(error.message || "Не удалось загрузить каталог из базы данных.");
      })
      .finally(() => {
        if (!isMounted) {
          return;
        }
        setIsCatalogLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const bootstrapSession = async () => {
      const storedUser = getSessionUser();
      const storedToken = getAccessToken();

      if (!storedUser || !storedToken) {
        if (isMounted) {
          setIsAppReady(true);
        }
        return;
      }

      try {
        const [user, cart, userOrders] = await Promise.all([
          fetchCurrentUser(storedToken),
          fetchCart(storedToken),
          fetchOrders(storedToken),
        ]);

        if (!isMounted) {
          return;
        }

        saveSession({ user, token: storedToken });
        setAuthUser(user);
        setAccessToken(storedToken);
        setCartItems(cart);
        setOrders(userOrders);
      } catch {
        if (!isMounted) {
          return;
        }
        logoutLocalUser();
        setAuthUser(null);
        setAccessToken(null);
        setCartItems([]);
        setOrders([]);
      } finally {
        if (isMounted) {
          setIsAppReady(true);
        }
      }
    };

    bootstrapSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleApiError = (error, fallbackMessage) => {
    if (error?.status === 401) {
      logoutLocalUser();
      setAuthUser(null);
      setAccessToken(null);
      setCartItems([]);
      setOrders([]);
      setCurrentPage("auth");
    }

    setPageError(error?.message || fallbackMessage);
  };

  const goToCatalog = () => {
    setPageError("");
    setCurrentPage("catalog");
  };

  const addToCart = async (product) => {
    if (!authUser || !accessToken) {
      setPageError("Чтобы добавить товар в корзину из базы данных, сначала войдите в аккаунт.");
      setCurrentPage("auth");
      return;
    }

    try {
      const nextItem = await addCartItem(accessToken, product.productId ?? product.id, 1);
      setCartItems((prev) => {
        const existingItem = prev.find((item) => item.id === nextItem.id);
        if (existingItem) {
          return prev.map((item) => (item.id === nextItem.id ? nextItem : item));
        }
        return [...prev, nextItem];
      });
      setPageError("");
      setCurrentPage("cart");
    } catch (error) {
      handleApiError(error, "Не удалось добавить товар в корзину.");
    }
  };

  const increaseQty = async (item) => {
    try {
      const updatedItem = await updateCartItem(accessToken, item.id, item.qty + 1);
      setCartItems((prev) => prev.map((entry) => (entry.id === updatedItem.id ? updatedItem : entry)));
      setPageError("");
    } catch (error) {
      handleApiError(error, "Не удалось увеличить количество товара.");
    }
  };

  const decreaseQty = async (item) => {
    if (item.qty <= 1) {
      await removeFromCart(item);
      return;
    }

    try {
      const updatedItem = await updateCartItem(accessToken, item.id, item.qty - 1);
      setCartItems((prev) => prev.map((entry) => (entry.id === updatedItem.id ? updatedItem : entry)));
      setPageError("");
    } catch (error) {
      handleApiError(error, "Не удалось уменьшить количество товара.");
    }
  };

  const removeFromCart = async (item) => {
    try {
      await deleteCartItem(accessToken, item.id);
      setCartItems((prev) => prev.filter((entry) => entry.id !== item.id));
      setPageError("");
    } catch (error) {
      handleApiError(error, "Не удалось удалить товар из корзины.");
    }
  };

  const handleAuthSuccess = async (user) => {
    const token = getAccessToken();
    if (!token) {
      setPageError("Сессия не была сохранена после входа.");
      return;
    }

    try {
      const [cart, userOrders] = await Promise.all([fetchCart(token), fetchOrders(token)]);
      setAuthUser(user);
      setAccessToken(token);
      setCartItems(cart);
      setOrders(userOrders);
      setPageError("");
      setCurrentPage("account");
    } catch (error) {
      handleApiError(error, "Не удалось загрузить данные пользователя.");
    }
  };

  const handleLogout = () => {
    logoutLocalUser();
    setAuthUser(null);
    setAccessToken(null);
    setCartItems([]);
    setOrders([]);
    setPageError("");
    setCurrentPage("home");
  };

  const handleProfileOpen = () => {
    setCurrentPage(authUser ? "account" : "auth");
  };

  const handleCheckoutOpen = () => {
    if (cartItems.length === 0) {
      return;
    }

    if (!authUser || !accessToken) {
      setCurrentPage("auth");
      return;
    }

    setCurrentPage("checkout");
  };

  const handleOrderSubmit = async ({ address, paymentMethod }) => {
    try {
      const newOrder = await createOrder(accessToken, {
        address,
        paymentMethod: PAYMENT_LABELS[paymentMethod] ?? paymentMethod,
      });

      setOrders((prev) => [newOrder, ...prev]);
      setCartItems([]);
      setPageError("");
      setCurrentPage("account");
    } catch (error) {
      handleApiError(error, "Не удалось оформить заказ.");
    }
  };

  if (!isAppReady) {
    return null;
  }

  if (currentPage === "auth") {
    return (
      <>
        <AuthPage
          onBackHome={() => setCurrentPage("home")}
          onAuthSuccess={handleAuthSuccess}
        />
        {pageError ? <p className="catalog-empty">{pageError}</p> : null}
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
        {pageError ? <p className="catalog-empty">{pageError}</p> : null}
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
        {pageError ? <p className="catalog-empty">{pageError}</p> : null}
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
        <CatalogPage
          products={products}
          onAddToCart={addToCart}
          isLoading={isCatalogLoading}
          error={catalogError || pageError}
        />
      ) : currentPage === "home" ? (
        <>
          <Main1 />
          {pageError ? <p className="catalog-empty">{pageError}</p> : null}
          <Popular products={products} onAddToCart={addToCart} goToCatalog={goToCatalog} />
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
