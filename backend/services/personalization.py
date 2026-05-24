from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from math import sqrt
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from data_pipeline.tag_normalizer import BROAD_STOP_TAGS, TAG_META, normalize_tags
except Exception:  # pragma: no cover - defensive fallback for unusual launch paths
    BROAD_STOP_TAGS = {
        "Информационные технологии",
        "Учебные и академические дисциплины",
        "Языки программирования",
        "Разработка программного обеспечения",
        "Software Development",
        "Programming",
    }
    TAG_META: dict[str, dict[str, str]] = {}

    def normalize_tags(raw_tags: list[str] | None):
        class _Result:
            normalized_tags = [
                tag for tag in (raw_tags or []) if isinstance(tag, str) and tag not in BROAD_STOP_TAGS
            ]

        return _Result()


from services.query_understanding import QueryIntent, build_query_scope, understand_query


AREA_TAGS = {
    "Artificial Intelligence",
    "Backend",
    "Computer Vision",
    "Cybersecurity",
    "Data Analysis",
    "Data Analytics",
    "Data Science",
    "Databases",
    "Deep Learning",
    "DevOps",
    "Frontend",
    "Machine Learning",
    "Natural Language Processing",
    "Web Development",
}

BASE_TECH_TAGS = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C++",
    "C#",
    "Go",
    "SQL",
}

PERSONALIZATION_CAP = 2.5


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def parse_vector(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        parsed: Any = None
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(cleaned)
                break
            except (ValueError, SyntaxError, json.JSONDecodeError):
                parsed = None
        if parsed is None:
            compact = cleaned.strip("[]()")
            parts = re.split(r"[\s,]+", compact)
            parsed = [part for part in parts if part]
        if isinstance(parsed, (list, tuple)):
            try:
                return [float(item) for item in parsed]
            except (TypeError, ValueError):
                return None
    return None


def get_course_tags(course: dict) -> list[str]:
    return course.get("normalized_tags") or course.get("tags") or []


def get_scoring_tags(course: dict) -> list[str]:
    raw_tags = get_course_tags(course)
    normalized = normalize_tags(raw_tags).normalized_tags
    cleaned_tags: list[str] = []
    for tag in normalized:
        if tag in BROAD_STOP_TAGS:
            continue
        _append_unique(cleaned_tags, tag)
    return cleaned_tags


def is_specific_tag(tag: str) -> bool:
    return tag not in AREA_TAGS and tag not in BASE_TECH_TAGS


def tag_weight(tag: str) -> float:
    if tag in BASE_TECH_TAGS:
        return 0.4
    level = TAG_META.get(tag, {}).get("level")
    if level in {"tool", "framework"}:
        return 1.5
    if level == "area" or tag in AREA_TAGS:
        return 0.8
    return 1.0


def cosine_similarity(left: Any, right: Any) -> float:
    left_vector = parse_vector(left)
    right_vector = parse_vector(right)
    if not left_vector or not right_vector or len(left_vector) != len(right_vector):
        return 0.0
    left_norm = sqrt(sum(value * value for value in left_vector))
    right_norm = sqrt(sum(value * value for value in right_vector))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return round(sum(a * b for a, b in zip(left_vector, right_vector)) / (left_norm * right_norm), 6)


def _centroid(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    length = len(vectors[0])
    same_length_vectors = [vector for vector in vectors if len(vector) == length]
    if not same_length_vectors:
        return None
    return [
        sum(vector[index] for vector in same_length_vectors) / len(same_length_vectors)
        for index in range(length)
    ]


def _empty_query_intent() -> QueryIntent:
    return QueryIntent(
        tags=[],
        primary_tags=[],
        confidence=0.0,
        exact_matches=[],
        semantic_matches=[],
    )


def extract_query_intent_tags(query: str) -> list[str]:
    return understand_query(query).tags


def _intent_tags(query_intent: QueryIntent | None) -> list[str]:
    return list(query_intent.tags if query_intent else [])


def _candidate_in_query_scope(candidate_tags: list[str], query_intent: QueryIntent | None) -> bool:
    scope = build_query_scope(query_intent)
    return not scope or bool(set(candidate_tags) & scope)


def build_user_interest_profile(
    liked_courses: list[dict],
    *,
    query_intent: QueryIntent | None = None,
) -> dict:
    tag_counts = Counter()
    liked_course_ids: set[int] = set()
    liked_cluster_ids: set[int] = set()
    embeddings: list[list[float]] = []
    context_tag_counts = Counter()
    context_liked_cluster_ids: set[int] = set()
    context_embeddings: list[list[float]] = []
    context_liked_courses_count = 0
    query_scope = build_query_scope(query_intent)
    non_base_query_scope = {tag for tag in query_scope if tag not in BASE_TECH_TAGS}
    has_specific_primary = any(
        tag not in BASE_TECH_TAGS
        for tag in ((query_intent.primary_tags if query_intent else []) or [])
    )

    for course in liked_courses:
        if course.get("id") is not None:
            liked_course_ids.add(course["id"])
        course_tags = get_scoring_tags(course)
        tag_counts.update(course_tags)
        if course.get("cluster_id") is not None:
            liked_cluster_ids.add(course["cluster_id"])
        embedding = parse_vector(course.get("embedding"))
        if embedding:
            embeddings.append(embedding)
        course_scope_matches = set(course_tags) & query_scope
        has_meaningful_context_match = (
            bool(course_scope_matches)
            and (
                not has_specific_primary
                or not non_base_query_scope
                or bool(set(course_tags) & non_base_query_scope)
            )
        )
        if query_scope and has_meaningful_context_match:
            context_liked_courses_count += 1
            context_tags = [tag for tag in course_tags if tag in query_scope]
            context_tag_counts.update(context_tags)
            if course.get("cluster_id") is not None:
                context_liked_cluster_ids.add(course["cluster_id"])
            if embedding:
                context_embeddings.append(embedding)

    top_tags = [tag for tag, _ in tag_counts.most_common(5)]
    query_matched_liked_tags = [tag for tag, _ in context_tag_counts.most_common(5)]

    return {
        "active": bool(liked_courses),
        "liked_courses_count": len(liked_courses),
        "liked_course_ids": liked_course_ids,
        "tag_counts": tag_counts,
        "top_tags": top_tags,
        "liked_cluster_ids": liked_cluster_ids,
        "liked_embedding_centroid": _centroid(embeddings),
        "query_intent": query_intent or _empty_query_intent(),
        "query_intent_tags": _intent_tags(query_intent),
        "query_matched_liked_tags": query_matched_liked_tags,
        "context_liked_courses_count": context_liked_courses_count,
        "context_tag_counts": context_tag_counts,
        "context_liked_cluster_ids": context_liked_cluster_ids,
        "context_liked_embedding_centroid": _centroid(context_embeddings),
    }


def get_public_user_profile(profile: dict) -> dict:
    return {
        "active": bool(profile.get("active")),
        "liked_courses_count": int(profile.get("liked_courses_count") or 0),
        "top_tags": list(profile.get("top_tags") or []),
        "query_intent_tags": list(profile.get("query_intent_tags") or []),
        "query_matched_liked_tags": list(profile.get("query_matched_liked_tags") or []),
        "context_liked_courses_count": int(profile.get("context_liked_courses_count") or 0),
    }


def load_liked_courses(supabase: Any, user_id: str) -> list[dict]:
    likes_response = (
        supabase.table("user_likes")
        .select("course_id, created_at")
        .eq("user_id", user_id)
        .execute()
    )
    liked_ids = [
        row["course_id"]
        for row in (likes_response.data or [])
        if row.get("course_id") is not None
    ]
    if not liked_ids:
        return []

    courses_response = (
        supabase.table("courses")
        .select("id, title, url, difficulty, learners_count, rating, tags, normalized_tags, embedding, cluster_id, is_paid, price")
        .in_("id", liked_ids)
        .execute()
    )
    return courses_response.data or []


def _query_score(candidate_tags: list[str], query_intent: QueryIntent | None) -> float:
    score = 0.0
    candidate_set = set(candidate_tags)
    query_tags = _intent_tags(query_intent)
    query_scope = build_query_scope(query_intent)
    for tag in query_tags:
        if tag in candidate_set:
            score += max(tag_weight(tag), 0.4)
    scope_only_matches = (candidate_set & query_scope) - set(query_tags)
    if scope_only_matches:
        score += min(sum(tag_weight(tag) * 0.5 for tag in scope_only_matches), 0.8)
    return min(score, 2.0)


def base_course_score(course: dict, query_intent: QueryIntent | None, user_skills: dict) -> float:
    candidate_tags = get_scoring_tags(course)
    skill_terms = {skill.casefold() for skill in user_skills}
    value = float(course.get("similarity") or course.get("score") or course.get("match_score") or 0.0)

    value += _query_score(candidate_tags, query_intent)
    for tag in candidate_tags:
        if tag.casefold() in skill_terms:
            value += 0.5

    if course.get("domain") and course.get("domain") != "it":
        value -= 0.75
    value += min(float(course.get("learners_count") or 0), 100000.0) / 1000000.0
    value += float(course.get("rating") or 0) / 100.0
    return value


def _history_tag_score(matched_tags: list[str], *, query_aligned: bool) -> float:
    if query_aligned:
        return sum(tag_weight(tag) for tag in matched_tags)
    return sum(tag_weight(tag) for tag in matched_tags if tag in BASE_TECH_TAGS)


def _build_reason(
    *,
    matched_tags: list[str],
    query_matches: list[str],
    same_cluster: bool,
) -> str:
    non_base_matches = [tag for tag in matched_tags if tag not in BASE_TECH_TAGS]

    if non_base_matches:
        reason_tags = matched_tags[:3]
        return f"Похоже на ваши лайкнутые курсы по тегам: {', '.join(reason_tags)}"
    if matched_tags == ["Python"] and "Python" in query_matches:
        return "Подходит под запрос по Python"
    if query_matches:
        return f"Подходит под запрос по тегам: {', '.join(query_matches[:3])}"
    if same_cluster:
        return "Похоже на ваши лайкнутые курсы по тематическому кластеру"
    return "Подобрано по смысловому совпадению с запросом"


def personalize_course(
    course: dict,
    profile: dict,
    *,
    query_intent: QueryIntent | None,
    user_skills: dict,
) -> dict:
    enriched = dict(course)
    query_intent = query_intent or profile.get("query_intent") or _empty_query_intent()
    base_score = base_course_score(enriched, query_intent, user_skills)
    query_tags = _intent_tags(query_intent)
    candidate_tags = get_scoring_tags(enriched)
    query_matches = [tag for tag in candidate_tags if tag in query_tags]

    if not profile.get("active"):
        enriched["reason"] = _build_reason(
            matched_tags=[],
            query_matches=query_matches,
            same_cluster=False,
        )
        enriched["personalization"] = {
            "score": 0.0,
            "matched_tags": [],
            "same_cluster": False,
            "already_liked": False,
            "embedding_similarity": 0.0,
            "final_score": round(base_score, 6),
            "query_tags": query_tags,
        }
        return enriched

    query_aligned = _candidate_in_query_scope(candidate_tags, query_intent)
    tag_counts: Counter = profile.get("context_tag_counts") or Counter()
    matched_tags = [tag for tag in candidate_tags if tag in tag_counts]
    query_matches = [tag for tag in candidate_tags if tag in query_tags]

    tag_score = _history_tag_score(matched_tags, query_aligned=query_aligned)
    same_cluster = (
        bool(matched_tags)
        and enriched.get("cluster_id") in (profile.get("context_liked_cluster_ids") or set())
        and query_aligned
    )
    cluster_score = 0.2 if same_cluster else 0.0
    embedding_similarity = cosine_similarity(
        enriched.get("embedding"),
        profile.get("context_liked_embedding_centroid"),
    )
    if not query_aligned:
        embedding_similarity = 0.0

    positive_score = min(tag_score + cluster_score + embedding_similarity, PERSONALIZATION_CAP)
    already_liked = enriched.get("id") in (profile.get("liked_course_ids") or set())
    already_liked_penalty = -5.0 if already_liked else 0.0
    personalization_score = positive_score + already_liked_penalty
    final_score = base_score + personalization_score

    enriched["personalization"] = {
        "score": round(personalization_score, 6),
        "matched_tags": matched_tags,
        "same_cluster": same_cluster,
        "already_liked": already_liked,
        "embedding_similarity": embedding_similarity,
        "final_score": round(final_score, 6),
        "query_tags": query_tags,
    }
    enriched["reason"] = _build_reason(
        matched_tags=matched_tags,
        query_matches=query_matches,
        same_cluster=same_cluster,
    )
    return enriched


def personalize_courses(
    courses: list[dict],
    profile: dict,
    *,
    query_intent: QueryIntent | None = None,
    query: str | None = None,
    user_skills: dict,
    limit: int,
) -> list[dict]:
    query_intent = query_intent or profile.get("query_intent")
    if query_intent is None and query is not None:
        query_intent = understand_query(query)
    query_intent = query_intent or _empty_query_intent()
    enriched_courses = [
        personalize_course(course, profile, query_intent=query_intent, user_skills=user_skills)
        for course in courses
    ]
    return sorted(
        enriched_courses,
        key=lambda course: course["personalization"]["final_score"],
        reverse=True,
    )[:limit]
