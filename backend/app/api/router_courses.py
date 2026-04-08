from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.params import Depends
from numpy.ma.extras import unique

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
        skills = prefs.get("skills", {})
        goals = prefs.get("learning_goals", {})
        map_diffs = {
            "beginner": "easy",
            "medium": "normal",
            "hard": "hard"
        }
        recommendations = []
        used_topics = []
        for goal in goals[:2]:
            goal = goal.capitalize()
            query = supabase.table("courses").select("id","title","url","difficulty","is_paid","price","learners_count")
            query = query.contains("tags", [goal]).eq("difficulty","easy")
            response = query.order("learners_count",desc=True).limit(3).execute()
            if response.data:
                recommendations.extend(response.data)
                used_topics.append(f"Цель: {goal} (easy)")

        for skill, skill_level in list(skills.items())[:2]:
            target_diff = map_diffs.get(skill_level.lower(), "easy")
            query = supabase.table("courses").select("id","title","url","difficulty","is_paid","price","learners_count")
            query = query.contains("tags", [skill]).eq("difficulty", target_diff)
            response = query.order("learners_count", desc=True).limit(3).execute()
            if response.data:
                recommendations.extend(response.data)
                used_topics.append(f"Прокачка: {skill} ({target_diff})")
        if not recommendations:
            query = supabase.table("courses").select("id","title", "url", "difficulty", "is_paid", "price", "learners_count")
            query = query.order("learners_count", desc=True).limit(limit).execute()
            recommendations.extend(query.data)
            used_topics.append("Общая популярность")
        unique_courses = {course["id"]: course for course in recommendations}
        print(unique_courses)
        final_rec = sorted(unique_courses.values(), key=lambda c: c["learners_count"],reverse=True)[:limit]
        return {
            "strategy": "smart_baseline",
            "topics_used": used_topics,
            "results_count": len(final_rec),
            "courses": final_rec
        }



    except Exception as e:
        raise e