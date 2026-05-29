import uuid
from datetime import datetime, timedelta
import json
import jwt
from fastapi import APIRouter, Depends, HTTPException
from app.core.database import supabase
from app.schemas.models import UserPreferences, TextInput
from app.core.security import get_current_user_id
from app.api.router_courses import get_public_course
from services.llm_request import ask_yagpt
from services.personalization import load_liked_courses
import os

router = APIRouter(prefix="/api/users", tags=["Users"])

DEFAULT_PREFERENCES = {
    "skills": {},
    "learning_goals": [],
    "time_per_week": "medium",
}


@router.post("/parse-skills")
def parse_text_to_skills(user_text: TextInput):
    system_prompt = """
        Ты AI-ассистент образовательной IT-платформы. 
        Твоя задача — извлечь ВСЕ упомянутые ИТ-навыки и цели из текста пользователя.

        ПРАВИЛА:
        1. Нормализуй сленг (например: "питон" -> "Python").
        2. ВАЖНО: Если пользователь указывает ПРОФЕССИЮ или широкую область (например: "Дата аналитик", "Backend-разработчик", "GameDev"), НЕ пиши название профессии. Вместо этого разбей её на 2-3 конкретные базовые технологии/инструмента на английском языке, которые ему нужно выучить.
           - Пример: "хочу стать дата аналитиком" ->["SQL", "Pandas", "Statistics"]
           - Пример: "хочу во фронтенд" ->["JavaScript", "React", "HTML"]

        УРОВНИ НАВЫКОВ (строго):
        - "beginner" (низкий, основы)
        - "medium" (средний, пишу около года)
        - "high" (высокий, эксперт)

        ВЕРНИ СТРОГО JSON в таком формате (БЕЗ разметки Markdown):
        {
            "skills": {
                "Python": "beginner"
            },
            "learning_goals":["SQL", "Pandas", "Statistics"]
        }
        """
    try:
        raw_text = ask_yagpt(system_prompt=system_prompt, user_text=user_text.text, temperature=0.0)
        clean_result = raw_text.replace("```json", "").replace("```", "").strip()
        parsed_data = json.loads(clean_result)

        return {
            "status": "success",
            "data": parsed_data
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Модель вернула текст, а не JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    try:
        user_resp = supabase.table("users").select("preferences").eq("id", user_id).execute()
        preferences = DEFAULT_PREFERENCES
        if user_resp.data:
            preferences = {
                **DEFAULT_PREFERENCES,
                **(user_resp.data[0].get("preferences") or {}),
            }

        liked_courses = load_liked_courses(supabase, user_id)
        liked_course_ids = {course["id"] for course in liked_courses if course.get("id") is not None}
        public_liked_courses = [
            get_public_course(course, liked_course_ids)
            for course in liked_courses
        ]

        return {
            "status": "success",
            "profile": {
                "preferences": preferences,
                "liked_course_ids": sorted(liked_course_ids),
                "liked_courses_count": len(public_liked_courses),
                "liked_courses": public_liked_courses,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
