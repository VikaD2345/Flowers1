const SESSION_STORAGE_KEY = "flowersSessionUser";
const TOKEN_STORAGE_KEY = "flowersAccessToken";

export const saveSession = ({ user, token }) => {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
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

export const getAccessToken = () => localStorage.getItem(TOKEN_STORAGE_KEY);

export const logoutLocalUser = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  localStorage.removeItem(TOKEN_STORAGE_KEY);
};
