const ADMIN_ACCESS_TOKEN_KEY = "flowersAdminToken";
const ADMIN_REFRESH_TOKEN_KEY = "flowersAdminRefreshToken";

export function getAdminToken() {
  return localStorage.getItem(ADMIN_ACCESS_TOKEN_KEY);
}

export function getAdminRefreshToken() {
  return localStorage.getItem(ADMIN_REFRESH_TOKEN_KEY);
}

export function setAdminTokens({ accessToken, refreshToken }) {
  if (accessToken) {
    localStorage.setItem(ADMIN_ACCESS_TOKEN_KEY, accessToken);
  }
  if (refreshToken) {
    localStorage.setItem(ADMIN_REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function updateAdminAccessToken(token) {
  if (!token) {
    localStorage.removeItem(ADMIN_ACCESS_TOKEN_KEY);
    return;
  }
  localStorage.setItem(ADMIN_ACCESS_TOKEN_KEY, token);
}

export function updateAdminRefreshToken(token) {
  if (!token) {
    localStorage.removeItem(ADMIN_REFRESH_TOKEN_KEY);
    return;
  }
  localStorage.setItem(ADMIN_REFRESH_TOKEN_KEY, token);
}

export function clearAdminToken() {
  localStorage.removeItem(ADMIN_ACCESS_TOKEN_KEY);
  localStorage.removeItem(ADMIN_REFRESH_TOKEN_KEY);
}
