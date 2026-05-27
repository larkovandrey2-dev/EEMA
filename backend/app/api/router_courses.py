import os
from collections import defaultdict, Counter
from app.schemas.models import RecommendationInput
from fastapi import APIRouter, Query, HTTPException
from fastapi.params import Depends
from datetime import datetime, timezone
from app.core.security import get_current_user_id
from app.core.database import supabase
import json
from services.embed_query import embed_query
from services.difficulty_policy import (
    filter_courses_for_user_skills,
    normalize_user_skills,
    preferred_course_difficulty,
    profile_level_rank,
)
from services.personalization import (
    build_user_interest_profile,
    get_scoring_tags,
    get_public_user_profile,
    load_liked_courses,
    personalize_courses,
)
from services.query_understanding import QueryIntent, understand_query
router = APIRouter(prefix="/api/courses", tags=["Courses"])

RAG_MATCH_THRESHOLDS = [0.55, 0.45, 0.35]

BASE_MARKOV_TAGS = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C++",
    "C#",
    "Go",
    "SQL",
}

PUBLIC_COURSE_FIELDS = {
    "id",
    "title",
    "url",
    "difficulty",
    "learners_count",
    "rating",
    "tags",
    "is_paid",
    "price",
    "markov_reason",
    "cluster_reason",
    "reason",
    "personalization",
}

INTERNAL_COURSE_FIELDS = {
    "raw_tags",
    "normalized_tags",
    "tag_meta",
    "domain",
}

MARKOV_MATRIX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "../../ML/scripts/markov_matrix.json")
try:
    with open(MARKOV_MATRIX_PATH, "r", encoding="utf-8") as f:
        MARKOV_MATRIX = json.load(f)
except FileNotFoundError:
    MARKOV_MATRIX = {}
    print("Файл markov_matrix.json не найден")


def get_public_course(course: dict) -> dict:
    public_course = {
        key: value
        for key, value in course.items()
        if key in PUBLIC_COURSE_FIELDS and key not in INTERNAL_COURSE_FIELDS
    }
    if "tags" not in public_course:
        public_course["tags"] = course.get("normalized_tags") or course.get("tags") or []
    return public_course


def get_course_tags(course: dict) -> list:
    return get_scoring_tags(course)


def get_empty_advanced_response(query: str, user_profile: dict | None = None) -> dict:
    return {
        "strategy": "rag_plus_classic_ml",
        "search_query": query,
        "main_results": [],
        "ml_enrichment": {
            "anchor_course_title": "",
            "cluster_neighbors": [],
            "markov_roadmap": [],
            "user_profile": user_profile or {
                "active": False,
                "liked_courses_count": 0,
                "top_tags": [],
                "query_intent_tags": [],
                "query_matched_liked_tags": [],
                "context_liked_courses_count": 0,
            }
        }
    }


def match_courses_with_fallback(query_embedding: list, match_count: int):
    last_response = None
    for threshold in RAG_MATCH_THRESHOLDS:
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": match_count
        }
        response = supabase.rpc("match_courses", rpc_params).execute()
        last_response = response
        result_count = len(response.data or [])
        print(f"RAG match_courses threshold={threshold} count={result_count}")
        if response.data:
            return response
    return last_response


def get_markov_seed_tags(courses: list[dict], query_intent: QueryIntent | None, top_k: int = 3) -> list[str]:
    query_tags = list(query_intent.tags if query_intent else [])
    query_specific_tags = [tag for tag in (query_intent.primary_tags if query_intent else []) if tag not in BASE_MARKOV_TAGS]
    if not query_specific_tags:
        query_specific_tags = [tag for tag in query_tags if tag not in BASE_MARKOV_TAGS]

    course_tag_counts = Counter()
    for course in courses[:3]:
        course_tag_counts.update(get_course_tags(course))

    dominant_tags: list[str] = []
    if query_specific_tags:
        for tag in query_specific_tags:
            if tag in course_tag_counts or tag in MARKOV_MATRIX:
                dominant_tags.append(tag)
        if dominant_tags:
            return dominant_tags[:top_k]

    for tag, _ in course_tag_counts.most_common():
        if tag not in BASE_MARKOV_TAGS:
            dominant_tags.append(tag)
        if len(dominant_tags) >= top_k:
            break

    return dominant_tags


def get_markov_next_tags(current_tags: list, top_k: int = 2) -> list:
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
            if next_tag not in current_tags and next_tag not in STOP_TAGS:
                next_step_scores[next_tag] += prob
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
        skills = normalize_user_skills(prefs.get("skills", {}))
        goals = prefs.get("learning_goals", [])
        recommendations = []
        used_topics = []
        for goal in goals[:2]:
            goal = goal.capitalize()
            query = supabase.table("courses").select("id","title","url","difficulty","tags","is_paid","price","learners_count")
            query = query.contains("tags", [goal]).eq("difficulty","easy")
            response = query.order("learners_count",desc=True).limit(3).execute()
            if response.data:
                recommendations.extend(response.data)
                used_topics.append(f"Цель: {goal} (easy)")

        for skill, skill_level in list(skills.items())[:2]:
            target_diff = preferred_course_difficulty(skill_level)
            query = supabase.table("courses").select("id","title","url","difficulty","tags","is_paid","price","learners_count")
            query = query.contains("tags", [skill]).eq("difficulty", target_diff)
            response = query.order("learners_count", desc=True).limit(3).execute()
            if response.data:
                recommendations.extend(response.data)
                used_topics.append(f"Прокачка: {skill} ({target_diff})")
        recommendations = filter_courses_for_user_skills(recommendations, skills)
        if len(recommendations) < limit:
            query = supabase.table("courses").select("id","title", "url", "difficulty", "tags", "is_paid", "price", "learners_count")
            query = query.order("learners_count", desc=True).limit(limit * 5).execute()
            recommendations.extend(filter_courses_for_user_skills(query.data or [], skills))
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
        user_skills = normalize_user_skills(prefs.get("skills", {}))
        user_query = embed_query(req.query)
        liked_courses = load_liked_courses(supabase, user_id)
        query_intent = understand_query(req.query, query_embedding=user_query)
        user_interest_profile = build_user_interest_profile(liked_courses, query_intent=query_intent)
        public_user_profile = get_public_user_profile(user_interest_profile)

        rag_response = match_courses_with_fallback(user_query, req.limit * 5)
        if not rag_response.data:
            return get_empty_advanced_response(req.query, public_user_profile)

        candidate_courses = filter_courses_for_user_skills(rag_response.data, user_skills)
        if not candidate_courses:
            return get_empty_advanced_response(req.query, public_user_profile)
        courses = personalize_courses(
            candidate_courses,
            user_interest_profile,
            query_intent=query_intent,
            user_skills=user_skills,
            limit=req.limit,
        )
        if not courses:
            return get_empty_advanced_response(req.query, public_user_profile)
        anchor_course = courses[0]
        dominant_tags = get_markov_seed_tags(courses, query_intent, top_k=3)
        next_tags = get_markov_next_tags(dominant_tags, top_k=2)
        known_skills = [
            skill.lower()
            for skill, level in user_skills.items()
            if profile_level_rank(level) >= 2
        ]
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

            for c in filter_courses_for_user_skills(markov_response.data or [], user_skills):
                c["markov_reason"] = f"Логичный следующий шаг (Тема: {top_next_tag})"
                next_step_courses.append(get_public_course(c))

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
            for c in filter_courses_for_user_skills(cluster_response.data or [], user_skills):
                c["cluster_reason"] = "Похожие курсы по тематике (Кластеризация)"
                related_from_clusters.append(get_public_course(c))
        return {
            "strategy": "rag_plus_classic_ml",
            "search_query": req.query,
            # Основная выдача от RAG
            "main_results": [get_public_course(course) for course in courses],
            # Дополнительные данные от классического ML
            "ml_enrichment": {
                "anchor_course_title": anchor_course["title"],
                "cluster_neighbors": related_from_clusters,
                "markov_roadmap": next_step_courses,
                "user_profile": public_user_profile,
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

        return {
            "status": "success",
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
