import React from "react";
import { Eye, EyeOff } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ThemeButton } from "../../shared";
import { auth } from "../../shared/api/auth";
import "../registration/registration.css";

const AuthPage = () => {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage("");
    setLoading(true);

    try {
      await auth.login({ email, password });
      navigate("/", { replace: true });
    } catch {
      setErrorMessage("Неправильная почта или пароль.");
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => {
    if (errorMessage) {
      setErrorMessage("");
    }
  };

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
                Войдите в аккаунт, чтобы продолжить подбор курсов по вашим
                навыкам.
              </p>
            </div>
          </div>

          <h2 className="auth-title">Вход</h2>

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
              autoComplete="current-password"
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
            {loading ? "Входим..." : "Войти"}
          </button>

          <button
            type="button"
            className="auth-switch"
            onClick={() => navigate("/register")}
          >
            Регистрация
          </button>
        </form>
      </div>
    </div>
  );
};

export default AuthPage;
