from typing import Optional

from fastapi import APIRouter, Query
from app.core.database import supabase

router = APIRouter(prefix="/api/courses", tags=["Courses"])
@router.get("/recommend/baseline")
def get_recommend_baseline(
        tag: Optional[str] = Query(None, description="Фильтр по тегу"),
        limit: int = Query(10, description="Кол-во курсов в рекомендации")):
    try:
        query = supabase.table("courses").select("id, title, summary, url, difficulty, learners_count, rating, tags")
        if tag:
            query = query.contains("tags",tag.split())
        response = query.order("learners_count",desc=True).limit(limit).execute()
        return {"algorithm": "baseline",
                "results_count":len(response.data),
                "courses": response.data}
    except Exception as e:
        return {"error": str(e)}