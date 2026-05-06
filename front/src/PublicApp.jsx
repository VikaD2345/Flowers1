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
  logoutUser,
  refreshSession,
  updateCartItem,
  deleteCartItem,
} from "./api/publicApi";
import { getSessionUser, logoutLocalUser, saveSession } from "./utils/authStorage";

const PAYMENT_LABELS = {
  card: "Картой курьеру",
  cash: "Наличными курьеру",
};
const MAX_CART_ITEM_QTY = 30;

export default function PublicApp() {
  const [currentPage, setCurrentPage] = useState("home");
  const [authInitialMode, setAuthInitialMode] = useState("register");
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
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [currentPage]);

  useEffect(() => {
    if (currentPage === "cart" && (!authUser || !accessToken)) {
      setAuthInitialMode("register");
      setCurrentPage("auth");
    }
  }, [currentPage, authUser, accessToken]);

  useEffect(() => {
    let isMounted = true;

    const bootstrapSession = async () => {
      const storedUser = getSessionUser();

      if (storedUser && isMounted) {
        setAuthUser(storedUser);
      }

      try {
        const refreshPayload = await refreshSession();
        const nextToken = refreshPayload.access_token;
        const [user, cart, userOrders] = await Promise.all([
          fetchCurrentUser(nextToken),
          fetchCart(nextToken),
          fetchOrders(nextToken),
        ]);

        if (!isMounted) {
          return;
        }

        saveSession({ user });
        setAuthUser(user);
        setAccessToken(nextToken);
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
      setAuthInitialMode("login");
      setCurrentPage("auth");
      return;
    }

    setPageError(error?.message || fallbackMessage);
  };

  const refreshAccessToken = async () => {
    const refreshPayload = await refreshSession();
    const nextToken = refreshPayload.access_token;
    setAccessToken(nextToken);
    return nextToken;
  };

  const runAuthenticatedRequest = async (requestFn) => {
    if (!accessToken) {
      const error = new Error("Not authenticated");
      error.status = 401;
      throw error;
    }

    try {
      return await requestFn(accessToken);
    } catch (error) {
      if (error?.status !== 401) {
        throw error;
      }

      const nextToken = await refreshAccessToken();
      return requestFn(nextToken);
    }
  };

  const goToCatalog = () => {
    setPageError("");
    setCurrentPage("catalog");
  };

  const openAuthPage = (mode = "register", message = "") => {
    setAuthInitialMode(mode);
    setPageError(message);
    setCurrentPage("auth");
  };

  const handlePageNavigate = (page) => {
    if (page === "cart" && (!authUser || !accessToken)) {
      openAuthPage("register", "Чтобы открыть корзину, сначала зарегистрируйтесь.");
      return;
    }

    setPageError("");
    setCurrentPage(page);
  };

  const buildOptimisticCartItem = (product, qty) => {
    const productId = product.productId ?? product.id;
    return {
      ...product,
      id: `pending-${productId}-${Date.now()}`,
      cartItemId: null,
      productId,
      qty,
      isPending: true,
    };
  };

  const addToCart = async (product) => {
    if (!authUser || !accessToken) {
      openAuthPage("register", "Чтобы добавить товар в корзину, сначала зарегистрируйтесь.");
      return false;
    }

    const productId = product.productId ?? product.id;
    const previousCartItems = cartItems;
    const existingItem = cartItems.find((item) => item.productId === productId);
    if (existingItem && existingItem.qty >= MAX_CART_ITEM_QTY) {
      setPageError(`В корзину можно добавить не больше ${MAX_CART_ITEM_QTY} шт. одного товара.`);
      return false;
    }

    setCartItems((prev) => {
      const existingItem = prev.find((item) => item.productId === productId);
      if (existingItem) {
        return prev.map((item) =>
          item.productId === productId ? { ...item, qty: item.qty + 1, isPending: true } : item
        );
      }
      return [...prev, buildOptimisticCartItem(product, 1)];
    });
    setPageError("");

    try {
      const nextItem = await runAuthenticatedRequest((token) => addCartItem(token, productId, 1));
      setCartItems((prev) => {
        const result = [];
        let inserted = false;

        for (const item of prev) {
          if (item.productId === productId || item.id === nextItem.id) {
            if (!inserted) {
              result.push({ ...nextItem, isPending: false });
              inserted = true;
            }
            continue;
          }
          result.push(item);
        }

        if (!inserted) {
          result.push({ ...nextItem, isPending: false });
        }

        return result;
      });
      return true;
    } catch (error) {
      setCartItems(previousCartItems);
      handleApiError(error, "Не удалось добавить товар в корзину.");
      return false;
    }
  };

  const increaseQty = async (item) => {
    if (item.qty >= MAX_CART_ITEM_QTY) {
      setPageError(`В корзину можно добавить не больше ${MAX_CART_ITEM_QTY} шт. одного товара.`);
      return;
    }

    try {
      const updatedItem = await runAuthenticatedRequest((token) => updateCartItem(token, item.id, item.qty + 1));
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
      const updatedItem = await runAuthenticatedRequest((token) => updateCartItem(token, item.id, item.qty - 1));
      setCartItems((prev) => prev.map((entry) => (entry.id === updatedItem.id ? updatedItem : entry)));
      setPageError("");
    } catch (error) {
      handleApiError(error, "Не удалось уменьшить количество товара.");
    }
  };

  const removeFromCart = async (item) => {
    try {
      await runAuthenticatedRequest((token) => deleteCartItem(token, item.id));
      setCartItems((prev) => prev.filter((entry) => entry.id !== item.id));
      setPageError("");
    } catch (error) {
      handleApiError(error, "Не удалось удалить товар из корзины.");
    }
  };

  const handleAuthSuccess = async (user, token) => {
    if (!token) {
      setPageError("Сессия не была сохранена после входа.");
      return;
    }

    try {
      const [cart, userOrders] = await Promise.all([fetchCart(token), fetchOrders(token)]);
      setAuthUser(user);
      saveSession({ user });
      setAccessToken(token);
      setCartItems(cart);
      setOrders(userOrders);
      setPageError("");
      setCurrentPage("account");
    } catch (error) {
      handleApiError(error, "Не удалось загрузить данные пользователя.");
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch {
      // Local cleanup is still enough to close the UI session if the network is unavailable.
    }
    logoutLocalUser();
    setAuthUser(null);
    setAccessToken(null);
    setCartItems([]);
    setOrders([]);
    setPageError("");
    setCurrentPage("home");
  };

  const handleProfileOpen = () => {
    if (authUser) {
      setPageError("");
      setCurrentPage("account");
      return;
    }

    openAuthPage("register");
  };

  const handleCheckoutOpen = () => {
    if (cartItems.length === 0) {
      return;
    }

    if (!authUser || !accessToken) {
      openAuthPage("register", "Чтобы перейти к оформлению заказа, сначала зарегистрируйтесь.");
      return;
    }

    setCurrentPage("checkout");
  };

  const handleOrderSubmit = async ({ address, paymentMethod }) => {
    try {
      const newOrder = await runAuthenticatedRequest((token) => createOrder(token, {
        address,
        paymentMethod: PAYMENT_LABELS[paymentMethod] ?? paymentMethod,
      }));

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
          initialMode={authInitialMode}
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
          onNavigate={handlePageNavigate}
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
          onNavigate={handlePageNavigate}
          currentPage={currentPage}
          onOpenProfile={handleProfileOpen}
        />
        <CheckoutPage
          items={cartItems}
          onBackToCart={() => handlePageNavigate("cart")}
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
        onNavigate={handlePageNavigate}
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
          maxItemQty={MAX_CART_ITEM_QTY}
        />
      )}
      <Footer />
      <FlowerAssistant onAddToCart={addToCart} onOpenCatalog={goToCatalog} />
    </div>
  );
}
