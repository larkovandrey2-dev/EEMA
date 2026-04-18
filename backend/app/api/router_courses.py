from typing import Optional
from app.schemas.models import RecommendationInput
from fastapi import APIRouter, Query, HTTPException
from fastapi.params import Depends
from datetime import datetime, timezone
from app.core.security import get_current_user_id
from app.core.database import supabase
from services.embed_query import embed_query
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
        goals = prefs.get("learning_goals", [])
        map_diffs = {
            "beginner": "easy",
            "Beginner": "easy",
            "medium": "normal",
            "advanced": "hard",
            "hard": "hard",
            "Intermediate": "normal",
            "intermediate": "normal",
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
        if not recommendations or len(recommendations) < limit:
            query = supabase.table("courses").select("id","title", "url", "difficulty", "is_paid", "price", "learners_count")
            query = query.order("learners_count", desc=True).limit(limit).execute()
            recommendations.extend(query.data)
            used_topics.append("Общая популярность")
        unique_courses = {course["id"]: course for course in recommendations}
        final_rec = list(unique_courses.values())[:limit]
        print(final_rec)

        return {
            "strategy": "smart_baseline",
            "topics_used": used_topics,
            "results_count": len(final_rec),
            "courses": final_rec
        }



    except Exception as e:
        raise e


@router.post("/{course_id}/like")
def like_course(
        course_id: int,
        user_id: str = Depends(get_current_user_id)
):
    try:
        course_check = supabase.table("courses").select("id").eq("id", course_id).execute()
        if not course_check.data:
            raise HTTPException(status_code=404, detail="Курс не найден")
        supabase.table("user_likes").insert({
            "user_id": user_id,
            "course_id": course_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"status": "success", "message": "Курс добавлен в избранное"}

    except Exception as e:
        if "duplicate key value" in str(e).lower() or "23505" in str(e):
            return {"status": "info", "message": "Вы уже лайкнули этот курс"}
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{course_id}/like")
def unlike_course(
        course_id: int,
        user_id: str = Depends(get_current_user_id)
):
    try:
        response = supabase.table("user_likes") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("course_id", course_id) \
            .execute()

        if not response.data:
            return {"status": "info", "message": "Лайк не был поставлен ранее"}

        return {"status": "success", "message": "Курс удален из избранного"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/advanced")
def get_advanced_recommendations(
        req: RecommendationInput,
        user_id: str = Depends(get_current_user_id)
):
    try:
        user_query = embed_query(req.query)
        rpc_params = {
            "query_embedding": user_query,
            "match_threshold": 0.4,
            "match_count": req.limit
        }
        rag_response = supabase.rpc("match_courses", rpc_params).execute()
        if not rag_response.data:
            return {"status": "empty", "message": "Ничего не найдено по смыслу"}

        courses = rag_response.data
        anchor_course = courses[0]
        anchor_id = anchor_course["id"]
        related_from_clusters = []
        next_step_roadmap = []

        return {
            "strategy": "rag_plus_classic_ml",
            "search_query": req.query,
            # Основная выдача от RAG
            "main_results": courses,
            # Дополнительные данные от классического ML
            "ml_enrichment": {
                "anchor_course_title": anchor_course["title"],
                "cluster_neighbors": related_from_clusters,
                "markov_roadmap": next_step_roadmap
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
