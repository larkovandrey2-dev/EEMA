import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends
from app.core.database import supabase
from app.schemas.models import UserPreferences, TextInput
from app.core.security import get_current_user_id
import os

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("/profile")
def update_profile(
        prefs: UserPreferences,
        user_id: str = Depends(get_current_user_id)
):
    try:
        supabase.table("users").upsert(
            {"id": user_id,
             "preferences": prefs.dict()}
        ).execute()
        return {"status": "success", "message": "Профиль сохранен"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}


@router.get("/generate-test-token")
def generate_test_token():
    secret = os.getenv("JWT_SECRET")
    fake_user_id = str(uuid.uuid4())
    payload = {
        "sub": fake_user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    return {
        "message": "Скопируй этот токен и вставь в кнопку Authorize в Swagger",
        "user_id": fake_user_id,
        "token": token
    }
