import { useState } from "react";
import { fetchCurrentUser, loginUser, registerUser } from "../api/publicApi";
import { saveSession } from "../utils/authStorage";
import "./AuthPage.css";

const initialSubmitState = {
  isLoading: false,
  error: "",
  success: "",
};

function AuthPage({ initialMode = "register", onBackHome, onAuthSuccess }) {
  const [mode, setMode] = useState(initialMode);
  const [registerForm, setRegisterForm] = useState({
    username: "",
    password: "",
  });
  const [loginForm, setLoginForm] = useState({
    username: "",
    password: "",
  });
  const [registerState, setRegisterState] = useState(initialSubmitState);
  const [loginState, setLoginState] = useState(initialSubmitState);

  const switchMode = (nextMode) => {
    setMode(nextMode);
    if (nextMode === "register") {
      setLoginState((prev) => ({ ...prev, error: "", success: "" }));
      return;
    }
    setRegisterState((prev) => ({ ...prev, error: "", success: "" }));
  };

  const handleRegisterChange = ({ target }) => {
    const { name, value } = target;
    setRegisterForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleLoginChange = ({ target }) => {
    const { name, value } = target;
    setLoginForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleRegisterSubmit = async (event) => {
    event.preventDefault();

    if (!registerForm.username || !registerForm.password) {
      setRegisterState({
        isLoading: false,
        error: "Заполни все поля перед регистрацией.",
        success: "",
      });
      return;
    }

    setRegisterState({
      isLoading: true,
      error: "",
      success: "",
    });

    try {
      await registerUser(registerForm);
      const loginPayload = await loginUser(registerForm);
      const user = await fetchCurrentUser(loginPayload.access_token);
      saveSession({ user, token: loginPayload.access_token });
      setRegisterForm({
        username: "",
        password: "",
      });
      setLoginForm({
        username: "",
        password: "",
      });
      setRegisterState(initialSubmitState);
      setLoginState(initialSubmitState);
      onAuthSuccess?.(user);
    } catch (error) {
      setRegisterState({
        isLoading: false,
        error: error.message || "Ошибка соединения с сервером.",
        success: "",
      });
    }
  };

  const handleLoginSubmit = async (event) => {
    event.preventDefault();

    if (!loginForm.username || !loginForm.password) {
      setLoginState({
        isLoading: false,
        error: "Введи логин и пароль.",
        success: "",
      });
      return;
    }

    setLoginState({
      isLoading: true,
      error: "",
      success: "",
    });

    try {
      const loginPayload = await loginUser(loginForm);
      const user = await fetchCurrentUser(loginPayload.access_token);
      saveSession({ user, token: loginPayload.access_token });

      setLoginState({
        isLoading: false,
        error: "",
        success: "Вход выполнен успешно.",
      });
      setLoginForm((prev) => ({ ...prev, password: "" }));
      onAuthSuccess?.(user);
    } catch (error) {
      setLoginState({
        isLoading: false,
        error: error.message || "Ошибка соединения с сервером.",
        success: "",
      });
    }
  };

  return (
    <section className="register-page auth-page" aria-label="Вход и регистрация">
      <div className="register-left auth-left">
        <img src="./src/assets/Group 576.svg" alt="VAMS" className="register-logo" />
      </div>

      <div className="register-right auth-right">
        <button type="button" className="auth-back-link" onClick={onBackHome}>
          На главную
        </button>

        <div className={`register-card auth-card auth-card--${mode}`}>
          <div className="auth-switcher" aria-label="Переключение между входом и регистрацией">
            <button
              type="button"
              className={`auth-switcher-button ${mode === "register" ? "is-active" : ""}`}
              onClick={() => switchMode("register")}
            >
              Регистрация
            </button>
            <button
              type="button"
              className={`auth-switcher-button ${mode === "login" ? "is-active" : ""}`}
              onClick={() => switchMode("login")}
            >
              Вход
            </button>
          </div>

          <div className="auth-panels-viewport">
            <div className="auth-panels-track">
              <section className="auth-panel" aria-hidden={mode !== "register"}>
                <h1 className="register-title auth-title">РЕГИСТРАЦИЯ</h1>

                <form className="register-form" onSubmit={handleRegisterSubmit}>
                  <input
                    type="text"
                    name="username"
                    placeholder="Имя"
                    autoComplete="username"
                    value={registerForm.username}
                    onChange={handleRegisterChange}
                    disabled={registerState.isLoading}
                  />
                  <input
                    type="password"
                    name="password"
                    placeholder="Пароль"
                    autoComplete="new-password"
                    value={registerForm.password}
                    onChange={handleRegisterChange}
                    disabled={registerState.isLoading}
                  />
                  {registerState.error ? (
                    <p className="register-message register-message-error">{registerState.error}</p>
                  ) : null}
                  {registerState.success ? (
                    <p className="register-message register-message-success">{registerState.success}</p>
                  ) : null}
                  <button type="submit" className="register-submit" disabled={registerState.isLoading}>
                    {registerState.isLoading ? "Отправка..." : "Зарегистрироваться"}
                  </button>
                </form>
              </section>

              <section className="auth-panel" aria-hidden={mode !== "login"}>
                <h1 className="register-title auth-title">ВХОД</h1>

                <form className="register-form" onSubmit={handleLoginSubmit}>
                  <input
                    type="text"
                    name="username"
                    placeholder="Имя"
                    autoComplete="username"
                    value={loginForm.username}
                    onChange={handleLoginChange}
                    disabled={loginState.isLoading}
                  />
                  <input
                    type="password"
                    name="password"
                    placeholder="Пароль"
                    autoComplete="current-password"
                    value={loginForm.password}
                    onChange={handleLoginChange}
                    disabled={loginState.isLoading}
                  />
                  {loginState.error ? <p className="register-message register-message-error">{loginState.error}</p> : null}
                  {loginState.success ? (
                    <p className="register-message register-message-success">{loginState.success}</p>
                  ) : null}
                  <button type="submit" className="register-submit" disabled={loginState.isLoading}>
                    {loginState.isLoading ? "Входим..." : "Войти"}
                  </button>
                </form>

              </section>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default AuthPage;
