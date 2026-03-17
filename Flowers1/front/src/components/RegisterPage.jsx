import "../main.css";

const RegisterPage = ({ onOpenLogin }) => {
  return (
    <section className="register-page" aria-label="Регистрация">

      <div className="register-left">
        <img src="./src/assets/Group 576.svg" alt="VAMS" className="register-logo" />
      </div>

      <div className="register-right">

        <div className="register-card">
          <h1 className="register-title">РЕГИСТРАЦИЯ</h1>

          <form className="register-form" onSubmit={(event) => event.preventDefault()}>
            <input type="text" placeholder="Имя" />
            <input type="email" placeholder="Email" />
            <input type="password" placeholder="Пароль" />
            <button type="submit" className="register-submit">Зарегистрироваться</button>
          </form>

          <button type="button" className="register-login-link" onClick={onOpenLogin}>
            Уже есть аккаунт? Войти
          </button>
        </div>
      </div>
    </section>
  );
};

export default RegisterPage;
