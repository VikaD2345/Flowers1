const SESSION_STORAGE_KEY = "flowersSessionUser";

export const saveSession = ({ user }) => {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
};

export const getSessionUser = () => {
  const rawSessionUser = localStorage.getItem(SESSION_STORAGE_KEY);

  if (!rawSessionUser) {
    return null;
  }

  try {
    return JSON.parse(rawSessionUser);
  } catch {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
};

export const logoutLocalUser = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
};
