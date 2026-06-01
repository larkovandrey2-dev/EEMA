import pytest
from fastapi import HTTPException


def test_get_cors_origins_from_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://eema.vercel.app, http://localhost:3000/")

    from app.core.config import get_cors_origins

    assert get_cors_origins() == ["https://eema.vercel.app", "http://localhost:3000"]


def test_generate_test_token_is_disabled_by_default(monkeypatch):
    monkeypatch.setenv("ENABLE_TEST_TOKEN_ENDPOINT", "false")

    from app.api import router_user

    with pytest.raises(HTTPException) as exc_info:
        router_user.generate_test_token()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not found"
