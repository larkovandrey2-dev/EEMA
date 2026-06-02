import React from "react";
import { Eye, EyeOff } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ThemeButton } from "../../shared";
import { auth } from "../../shared/api/auth";
import { getApiErrorMessage } from "../../shared/api/utils/error";
import "./registration.css";

const RegistrationPage = () => {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState("");
  const [registrationComplete, setRegistrationComplete] = React.useState(false);
  const [showPassword, setShowPassword] = React.useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage("");
    setLoading(true);

    try {
      await auth.register({ email, password });
      setPassword("");
      setRegistrationComplete(true);
    } catch (e) {
      setErrorMessage(
        getApiErrorMessage(
          e,
          "Не удалось зарегистрироваться. Проверьте почту и пароль."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => {
    if (errorMessage) {
      setErrorMessage("");
    }
  };

  if (registrationComplete) {
    return (
      <div className="auth-wrapper">
        <div className="auth-container">
          <div className="auth-top">
            <ThemeButton />
          </div>

          <div className="auth-form">
            <div className="auth-brand">
              <div className="auth-logo">E</div>
              <div>
                <p className="auth-kicker">EEMA</p>
                <h1 className="auth-welcome">Проверьте почту</h1>
                <p className="auth-description">
                  Мы отправили письмо для подтверждения аккаунта на {email}.
                  После подтверждения можно будет войти в EEMA.
                </p>
              </div>
            </div>

            <div className="auth-success" role="status">
              Если письма нет, проверьте папку спам или попробуйте
              зарегистрироваться ещё раз через пару минут.
            </div>

            <button
              type="button"
              className="auth-button"
              onClick={() => navigate("/auth")}
            >
              Перейти ко входу
            </button>

            <button
              type="button"
              className="auth-switch"
              onClick={() => setRegistrationComplete(false)}
            >
              Изменить почту
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-container">
        <div className="auth-top">
          <ThemeButton />
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-brand">
            <div className="auth-logo">E</div>
            <div>
              <p className="auth-kicker">EEMA</p>
              <h1 className="auth-welcome">Добро пожаловать в EEMA</h1>
              <p className="auth-description">
                Создайте аккаунт, чтобы сохранить профиль навыков и получать
                персональные рекомендации.
              </p>
            </div>
          </div>

          <h2 className="auth-title">Регистрация</h2>

          <input
            className="auth-input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              clearError();
            }}
            autoComplete="email"
            aria-invalid={!!errorMessage}
            required
          />

          <div className="auth-password-field">
            <input
              className="auth-input auth-password-input"
              type={showPassword ? "text" : "password"}
              placeholder="Пароль"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                clearError();
              }}
              autoComplete="new-password"
              minLength={6}
              aria-invalid={!!errorMessage}
              required
            />
            <button
              type="button"
              className="auth-password-toggle"
              onClick={() => setShowPassword((current) => !current)}
              aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
              aria-pressed={showPassword}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          {errorMessage && (
            <div className="auth-error" role="alert">
              {errorMessage}
            </div>
          )}

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? "Создаем аккаунт..." : "Зарегистрироваться"}
          </button>

          <button
            type="button"
            className="auth-switch"
            onClick={() => navigate("/auth")}
          >
            Авторизация
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegistrationPage;
