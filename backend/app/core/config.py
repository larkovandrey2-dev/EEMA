import os

from dotenv import load_dotenv


load_dotenv()

DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")


def get_env(name: str, *, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_ORIGIN") or ""
    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return origins or list(DEFAULT_CORS_ORIGINS)


def is_test_token_endpoint_enabled() -> bool:
    return (os.getenv("ENABLE_TEST_TOKEN_ENDPOINT") or "false").casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }
