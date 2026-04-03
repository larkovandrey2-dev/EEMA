from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import supabase

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

class UserAuth(BaseModel):
    email: str
    password: str

@router.post("/register")
def register_user(credentials: UserAuth):
    try:
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password,
        })
        return {
            "status": "success",
            "message": "Пользователь зарегистрирован",
            "user_id": response.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login_user(credentials: UserAuth):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })
        return {
            "status": "success",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "Bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_session(req: RefreshRequest):
    try:
        response = supabase.auth.refresh_session(req.refresh_token)

        return {
            "status": "success",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "Bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Сессия истекла. Пожалуйста, войдите заново.")