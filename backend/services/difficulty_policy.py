from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.tag_normalizer import normalize_tags


PROFILE_LEVEL_RANKS = {
    "beginner": 1,
    "easy": 1,
    "intermediate": 2,
    "medium": 2,
    "normal": 2,
    "advanced": 3,
    "high": 3,
    "hard": 3,
    "expert": 3,
}

COURSE_DIFFICULTY_RANKS = {
    "easy": 1,
    "normal": 2,
    "hard": 3,
}


def profile_level_rank(value: object) -> int:
    if not isinstance(value, str):
        return 1
    return PROFILE_LEVEL_RANKS.get(value.strip().casefold(), 1)


def preferred_course_difficulty(value: object) -> str:
    rank = profile_level_rank(value)
    return {1: "easy", 2: "normal", 3: "hard"}[rank]


def _canonical_terms(values: list[str]) -> list[str]:
    canonical: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        normalized = normalize_tags([value]).normalized_tags
        terms = normalized or [value.strip()]
        for term in terms:
            if term not in canonical:
                canonical.append(term)
    return canonical


def normalize_user_skills(skills: dict | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_skill, raw_level in (skills or {}).items():
        if not isinstance(raw_skill, str):
            continue
        for skill in _canonical_terms([raw_skill]):
            existing_level = normalized.get(skill)
            if existing_level is None or profile_level_rank(raw_level) > profile_level_rank(existing_level):
                normalized[skill] = str(raw_level)
    return normalized


def course_allowed_for_user_skills(course: dict, user_skills: dict | None) -> bool:
    normalized_skills = normalize_user_skills(user_skills)
    constrained_tags = {
        skill.casefold()
        for skill, level in normalized_skills.items()
        if profile_level_rank(level) >= 3
    }
    if not constrained_tags:
        return True

    course_tags = {tag.casefold() for tag in _canonical_terms(course.get("normalized_tags") or course.get("tags") or [])}
    if not (course_tags & constrained_tags):
        return True

    difficulty = course.get("difficulty")
    rank = COURSE_DIFFICULTY_RANKS.get(str(difficulty).casefold()) if difficulty is not None else None
    return rank is not None and rank >= 2


def filter_courses_for_user_skills(courses: list[dict], user_skills: dict | None) -> list[dict]:
    return [course for course in courses if course_allowed_for_user_skills(course, user_skills)]
