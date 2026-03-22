const ORDERS_STORAGE_KEY = "flowersOrders";

const readOrders = () => {
  const rawOrders = localStorage.getItem(ORDERS_STORAGE_KEY);

  if (!rawOrders) {
    return [];
  }

  try {
    const parsedOrders = JSON.parse(rawOrders);
    return Array.isArray(parsedOrders) ? parsedOrders : [];
  } catch {
    return [];
  }
};

const writeOrders = (orders) => {
  localStorage.setItem(ORDERS_STORAGE_KEY, JSON.stringify(orders));
};

export const getOrdersByUserId = (userId) => {
  if (!userId) {
    return [];
  }

  return readOrders()
    .filter((order) => order.userId === userId)
    .sort((left, right) => new Date(right.createdAt) - new Date(left.createdAt));
};

export const createOrder = ({ userId, items, address, paymentMethod }) => {
  const orders = readOrders();
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const itemCount = items.reduce((sum, item) => sum + item.qty, 0);

  const order = {
    id: `FL-${Date.now()}`,
    userId,
    address,
    paymentMethod,
    createdAt: new Date().toISOString(),
    status: "Создан",
    total,
    itemCount,
    items: items.map((item) => ({
      id: item.id,
      title: item.title,
      description: item.description,
      image: item.image,
      price: item.price,
      qty: item.qty,
    })),
  };

  const nextOrders = [order, ...orders];
  writeOrders(nextOrders);

  return order;
};
