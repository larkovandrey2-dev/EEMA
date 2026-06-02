import axios from "axios";

const translateApiErrorMessage = (message: string) => {
  const normalized = message.toLowerCase();

  if (
    normalized.includes("invalid login credentials") ||
    normalized.includes("invalid email or password")
  ) {
    return "Неправильная почта или пароль.";
  }

  if (normalized.includes("email not confirmed")) {
    return "Подтвердите почту перед входом.";
  }

  if (
    normalized.includes("user already registered") ||
    normalized.includes("already registered") ||
    normalized.includes("already exists")
  ) {
    return "Пользователь с такой почтой уже зарегистрирован.";
  }

  if (
    normalized.includes("invalid email") ||
    normalized.includes("email address is invalid") ||
    normalized.includes("unable to validate email")
  ) {
    return "Некорректная почта.";
  }

  if (
    normalized.includes("password should be at least") ||
    normalized.includes("weak password") ||
    normalized.includes("password")
  ) {
    return "Проверьте пароль: он не подходит по требованиям.";
  }

  return message;
};

export const getApiErrorMessage = (
  error: unknown,
  fallback = "Не удалось выполнить запрос. Попробуйте еще раз."
) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    const message = error.response?.data?.message;

    if (typeof detail === "string" && detail.trim()) {
      return translateApiErrorMessage(detail);
    }

    if (Array.isArray(detail)) {
      const validationMessage = detail
        .map((item) => item?.msg || item?.message || JSON.stringify(item))
        .filter(Boolean)
        .join("; ");

      if (validationMessage) {
        return translateApiErrorMessage(validationMessage);
      }
    }

    if (typeof message === "string" && message.trim()) {
      return translateApiErrorMessage(message);
    }

    if (error.message) {
      return translateApiErrorMessage(error.message);
    }
  }

  if (error instanceof Error && error.message) {
    return translateApiErrorMessage(error.message);
  }

  return fallback;
};
