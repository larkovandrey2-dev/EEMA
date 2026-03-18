from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.params import Depends
from app.core.security import get_current_user_id
from app.core.database import supabase

router = APIRouter(prefix="/api/courses", tags=["Courses"])
@router.get("/recommend/baseline")
def get_recommend_baseline(
        user_id: str = Depends(get_current_user_id),
        limit: int = Query(10, description="Кол-во курсов в рекомендации")):
    try:
        user_resp = supabase.table("users").select("preferences").eq("id", user_id).execute()
        if not user_resp.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        prefs = user_resp.data[0].get("preferences", {})
        target_tag = None
        if "skills" in prefs and len(prefs["skills"]) > 0:
            target_tag = list(prefs["skills"].keys())[0]
        query = supabase.table("courses").select("id, title, url, difficulty, learners_count, tags")
        if target_tag:
            query = query.contains("tags", [target_tag])
        response = query.order("learners_count", desc=True).limit(limit).execute()
        return {
            "strategy": "personalized_baseline",
            "user_interest_used": target_tag or "Общая популярность",
            "courses": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))