import { useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8100").replace(/\/$/, "");
const REGISTER_URL = import.meta.env.VITE_REGISTER_URL ?? `${API_BASE_URL}/auth/register`;
const USERNAME_MAX_LENGTH = 50;
const PASSWORD_MAX_LENGTH = 30;

const formatRegisterError = (payload) => {
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => {
      const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : "";
      const label = field === "username" ? "Логин" : field === "password" ? "Пароль" : "Поле";
      if (item?.type === "string_too_long") {
        return `${label} должен быть не длиннее ${item?.ctx?.max_length ?? "допустимого количества"} символов.`;
      }
      if (item?.type === "string_too_short") {
        return `${label} должен быть не короче ${item?.ctx?.min_length ?? "допустимого количества"} символов.`;
      }
      if (item?.type === "missing") {
        return `${label} обязателен для заполнения.`;
      }
      return `${label} заполнен некорректно.`;
    }).join(" ");
  }
  return payload?.detail || payload?.message || "Не удалось зарегистрировать пользователя.";
};

const RegisterPage = ({ onOpenLogin }) => {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [submitState, setSubmitState] = useState({
    isLoading: false,
    error: "",
    success: "",
  });

  const handleChange = ({ target }) => {
    const { name, value } = target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!formData.username || !formData.password) {
      setSubmitState({
        isLoading: false,
        error: "Заполни все поля перед регистрацией.",
        success: "",
      });
      return;
    }

    setSubmitState({
      isLoading: true,
      error: "",
      success: "",
    });

    try {
      const response = await fetch(REGISTER_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      let data = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        throw new Error(formatRegisterError(data));
      }

      setSubmitState({
        isLoading: false,
        error: "",
        success: "Регистрация прошла успешно. Теперь можно войти в аккаунт.",
      });
      setFormData({
        username: "",
        password: "",
      });
    } catch (error) {
      setSubmitState({
        isLoading: false,
        error: error.message || "Ошибка соединения с сервером.",
        success: "",
      });
    }
  };

  return (
    <section className="register-page" aria-label="Регистрация">
      <div className="register-left">
        <img src="./src/assets/Group 576.svg" alt="VAMS" className="register-logo" />
      </div>

      <div className="register-right">
        <div className="register-card">
          <h1 className="register-title">РЕГИСТРАЦИЯ</h1>

          <form className="register-form" onSubmit={handleSubmit}>
            <input 
              type="text"
              name="username"
              maxLength={USERNAME_MAX_LENGTH}
              placeholder="Имя"
              value={formData.username}
              onChange={handleChange}
              disabled={submitState.isLoading}
            />
            <input
              type="password"
              name="password"
              maxLength={PASSWORD_MAX_LENGTH}
              placeholder="Пароль"
              value={formData.password}
              onChange={handleChange}
              disabled={submitState.isLoading}
            />
            {submitState.error ? <p className="register-message register-message-error">{submitState.error}</p> : null}
            {submitState.success ? (
              <p className="register-message register-message-success">{submitState.success}</p>
            ) : null}
            <button type="submit" className="register-submit" disabled={submitState.isLoading}>
              {submitState.isLoading ? "Отправка..." : "Зарегистрироваться"}
            </button>
          </form>
        </div>
      </div>
    </section>
  );
};
export default RegisterPage;
