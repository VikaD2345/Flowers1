const SESSION_STORAGE_KEY = "flowersSessionUser";
const ACCESS_TOKEN_STORAGE_KEY = "flowersAccessToken";
const REFRESH_TOKEN_STORAGE_KEY = "flowersRefreshToken";

export const saveSession = ({ user, token, accessToken, refreshToken }) => {
  const nextAccessToken = accessToken ?? token ?? "";

  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, nextAccessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken);
  }
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

export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);

export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);

export const updateAccessToken = (token) => {
  if (!token) {
    localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
};

export const updateRefreshToken = (token) => {
  if (!token) {
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    return;
  }
  localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
};

export const logoutLocalUser = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
};
