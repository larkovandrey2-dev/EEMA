import os
import sys

current_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_path, '..', '..', '..')) # Поднимаемся на 2 уровня: из app -> в backend -> в EEMA
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from collections import defaultdict, Counter
from typing import Optional
from app.schemas.models import RecommendationInput
from fastapi import APIRouter, Query, HTTPException
from fastapi.params import Depends
from datetime import datetime, timezone
from app.core.security import get_current_user_id
from app.core.database import supabase
import json
from services.embed_query import embed_query
from data_pipeline.db_client import get_updating_date

router = APIRouter(prefix="/api/courses", tags=["Courses"])

MARKOV_MATRIX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "../../ML/scripts/markov_matrix.json")
try:
    with open(MARKOV_MATRIX_PATH, "r", encoding="utf-8") as f:
        MARKOV_MATRIX = json.load(f)
except FileNotFoundError:
    MARKOV_MATRIX = {}
    print("Файл markov_matrix.json не найден")

def get_markov_next_tags(current_tags: list, top_k:int = 2) -> list:
    STOP_TAGS = {
        "Информационные технологии",
        "Языки программирования",
        "Разработка программного обеспечения",
        "Programming",
        "Software and Development Tools",
        "Учебные и академические дисциплины",
        "Informatics",
        "Digital Literacy"
    }
    meaningful_tags = [tag for tag in current_tags if tag not in STOP_TAGS]
    next_step_scores = defaultdict(float)
    for tag in meaningful_tags:
        transitions = MARKOV_MATRIX.get(tag, {})
        for next_tag, prob in transitions.items():
            if next_tag not in current_tags:
                next_step_scores[next_tag] += prob
    print(next_step_scores)
    sorted_steps = sorted(next_step_scores.items(), key=lambda x: x[1], reverse=True)
    return [tag for tag, score in sorted_steps[:top_k]]





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
        user_resp = supabase.table("users").select("preferences").eq("id", user_id).execute()
        prefs = user_resp.data[0].get("preferences", {}) if user_resp.data else {}
        user_skills = prefs.get("skills", {})
        LEVEL_WEIGHTS = {
            "beginner": 1, "easy": 1,
            "medium": 2, "normal": 2,
            "hard": 3, "expert": 3, "high": 3
        }
        user_skills_numeric = {
            k.lower(): LEVEL_WEIGHTS.get(v.lower(), 1)
            for k, v in user_skills.items()
        }
        user_query = embed_query(req.query)
        rpc_params = {
            "query_embedding": user_query,
            "match_threshold": 0.55,
            "match_count": req.limit * 5
        }
        rag_response = supabase.rpc("match_courses", rpc_params).execute()
        if not rag_response.data:
            return {"status": "empty", "message": "Ничего не найдено"}
        expert_skills = [k.lower() for k, v in user_skills.items() if v in ["hard", "expert"]]

        filtered_courses = []
        for course in rag_response.data:
            course_diff_str = (course.get("difficulty") or "easy").lower()
            course_diff_num = LEVEL_WEIGHTS.get(course_diff_str, 1)

            course_tags_lower = [t.lower() for t in course.get("tags", [])]

            is_too_easy = False

            for tag in course_tags_lower:
                if tag in user_skills_numeric:
                    user_level_num = user_skills_numeric[tag]
                    if (user_level_num - course_diff_num) > 1:
                        is_too_easy = True
                        break
            if not is_too_easy:
                filtered_courses.append(course)
        if not filtered_courses:
            courses = rag_response.data[:req.limit]
        else:
            courses = filtered_courses[:req.limit]
        anchor_course = courses[0]
        all_top_tags = []
        for c in courses[:3]:
            all_top_tags.extend(c.get("tags", []))
        tag_counts = Counter(all_top_tags)
        dominant_tags = [tag for tag, count in tag_counts.most_common(3)]
        next_tags = get_markov_next_tags(dominant_tags, top_k=2)
        known_skills = [skill.lower() for skill, level in user_skills.items() if level in ["medium", "high", "expert", "hard", "normal"]]
        filtered_next_tags = []
        for tag in next_tags:
            if tag.lower() not in known_skills:
                filtered_next_tags.append(tag)
        next_tags = filtered_next_tags
        next_step_courses = []
        if next_tags:
            markov_query = supabase.table("courses").select("id, title, url, difficulty, learners_count, tags")\
                .neq("id", anchor_course["id"])
            top_next_tag = next_tags[0]
            markov_response = markov_query.contains("tags", [top_next_tag]) \
                .order("learners_count", desc=True) \
                .limit(2) \
                .execute()

            for c in markov_response.data:
                c["markov_reason"] = f"Логичный следующий шаг (Тема: {top_next_tag})"
                next_step_courses.append(c)

        anchor_emb = anchor_course["embedding"]
        anchor_id = anchor_course["id"]
        anchor_cluster_id = anchor_course["cluster_id"]
        related_from_clusters = []
        if anchor_cluster_id is not None and anchor_emb:
            cluster_params = {
                "target_embedding": anchor_emb,
                "target_cluster_id": anchor_cluster_id,
                "target_course_id": anchor_id,
                "match_count": 3
            }
            cluster_response = supabase.rpc("get_cluster_neighbors", cluster_params).execute()
            for c in cluster_response.data:
                c["cluster_reason"] = "Похожие курсы по тематике (Кластеризация)"
                related_from_clusters.append(c)
        return {
            "strategy": "rag_plus_classic_ml",
            "search_query": req.query,
            # Основная выдача от RAG
            "main_results": courses,
            # Дополнительные данные от классического ML
            "ml_enrichment": {
                "anchor_course_title": anchor_course["title"],
                "cluster_neighbors": related_from_clusters,
                "markov_roadmap": next_step_courses
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog")
def get_courses_catalog(
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(12, ge=1, le=50, description="Количество курсов на странице"),
        sort_by: str = Query("popular", description="Сортировка: popular, rating, new"),
        difficulty: str = Query(None, description="Фильтр по сложности: easy, normal, hard"),
        search: str = Query(None, description="Поиск по названию")
):
    try:
        start = (page - 1) * size
        end = start + size - 1

        query = supabase.table("courses").select(
            "id, title, url, difficulty, learners_count, rating, tags, is_paid, price",
            count="exact"
        )

        if difficulty:
            query = query.eq("difficulty", difficulty)
        if search:
            query = query.ilike("title", f"%{search}%")

        if sort_by == "popular":
            query = query.order("learners_count", desc=True)
        elif sort_by == "rating":
            query = query.order("rating", desc=True)
        elif sort_by == "new":
            query = query.order("id", desc=True)

        response = query.range(start, end).execute()

        update_date_obj = get_updating_date()
        update_date_str = update_date_obj.strftime('%Y-%m-%d %H:%M:%S') if update_date_obj else "Неизвестно"

        return {
            "status": "success",
            "update_date": update_date_str,
            "meta": {
                "current_page": page,
                "page_size": size,
                "total_items": response.count,
                "total_pages": (response.count + size - 1) // size if response.count else 0
            },
            "courses": response.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
