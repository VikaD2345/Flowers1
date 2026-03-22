import seedUsers from "../authUsers.json";

const USERS_STORAGE_KEY = "flowersUsers";
const SESSION_STORAGE_KEY = "flowersSessionUser";

const normalizeUser = (user) => ({
  id: user.id,
  username: user.username,
  password: user.password,
  role: user.role ?? "user",
});

const readStoredUsers = () => {
  const rawUsers = localStorage.getItem(USERS_STORAGE_KEY);

  if (!rawUsers) {
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(seedUsers));
    return seedUsers.map(normalizeUser);
  }

  try {
    const parsedUsers = JSON.parse(rawUsers);
    if (!Array.isArray(parsedUsers)) {
      throw new Error("Users payload is invalid.");
    }
    return parsedUsers.map(normalizeUser);
  } catch {
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(seedUsers));
    return seedUsers.map(normalizeUser);
  }
};

const writeStoredUsers = (users) => {
  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
};

export const getAllUsers = () => readStoredUsers();

export const registerLocalUser = ({ username, password }) => {
  const trimmedUsername = username.trim();
  const users = readStoredUsers();
  const existingUser = users.find(
    (user) => user.username.toLowerCase() === trimmedUsername.toLowerCase()
  );

  if (existingUser) {
    throw new Error("Пользователь с таким именем уже существует.");
  }

  const newUser = {
    id: users.reduce((maxId, user) => Math.max(maxId, user.id), 0) + 1,
    username: trimmedUsername,
    password,
    role: "user",
  };

  const nextUsers = [...users, newUser];
  writeStoredUsers(nextUsers);
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newUser));

  return newUser;
};

export const loginLocalUser = ({ username, password }) => {
  const trimmedUsername = username.trim();
  const users = readStoredUsers();
  const user = users.find(
    (item) =>
      item.username.toLowerCase() === trimmedUsername.toLowerCase() &&
      item.password === password
  );

  if (!user) {
    throw new Error("Неверное имя пользователя или пароль.");
  }

  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));

  return user;
};

export const getSessionUser = () => {
  const rawSessionUser = localStorage.getItem(SESSION_STORAGE_KEY);

  if (!rawSessionUser) {
    return null;
  }

  try {
    const sessionUser = normalizeUser(JSON.parse(rawSessionUser));
    const users = readStoredUsers();
    return users.find((user) => user.id === sessionUser.id) ?? null;
  } catch {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
};

export const logoutLocalUser = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
};
