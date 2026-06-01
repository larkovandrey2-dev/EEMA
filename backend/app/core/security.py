import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_env

SUPABASE_JWT = get_env("JWT_SECRET")
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SUPABASE_JWT, algorithms=["HS256"], audience="authenticated")
        return payload.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Неверный токен: {str(e)}")


def get_optional_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
):
    if credentials is None:
        return None
    return get_current_user_id(credentials)
