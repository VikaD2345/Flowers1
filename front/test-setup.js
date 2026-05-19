import "@testing-library/jest-dom/vitest";

function createStorageMock() {
  const store = new Map();

  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
    removeItem(key) {
      store.delete(String(key));
    },
    clear() {
      store.clear();
    },
  };
}

function ensureLocalStorage() {
  if (typeof window.localStorage?.clear === "function") {
    return window.localStorage;
  }

  const storageMock = createStorageMock();

  Object.defineProperty(window, "localStorage", {
    configurable: true,
    writable: true,
    value: storageMock,
  });

  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    writable: true,
    value: storageMock,
  });

  return storageMock;
}

beforeAll(() => {
  Object.defineProperty(window, "scrollTo", {
    writable: true,
    value: vi.fn(),
  });

  ensureLocalStorage();
});

beforeEach(() => {
  ensureLocalStorage().clear();
});
