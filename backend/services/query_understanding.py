from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.tag_normalizer import (  # noqa: E402
    ALIASES,
    BROAD_STOP_TAGS,
    CANONICAL_TAGS,
    TAG_META,
)


DEFAULT_TAXONOMY_CACHE_PATH = PROJECT_ROOT / "data_pipeline" / "taxonomy_embeddings.json"
TOKEN_STOPWORDS = {
    "and",
    "course",
    "data",
    "development",
    "learning",
    "analysis",
    "analytics",
    "online",
    "software",
    "разработка",
    "данных",
    "обучение",
    "курс",
    "анализ",
    "аналитика",
}
BASE_LANGUAGE_TAGS = {"Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go"}


@dataclass(frozen=True)
class QueryIntent:
    tags: list[str]
    primary_tags: list[str]
    confidence: float
    exact_matches: list[str]
    semantic_matches: list[dict]


def _empty_intent() -> QueryIntent:
    return QueryIntent(
        tags=[],
        primary_tags=[],
        confidence=0.0,
        exact_matches=[],
        semantic_matches=[],
    )


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _normalize_text(value: str) -> str:
    lowered = value.casefold()
    cleaned = re.sub(r"[_./+#-]+", " ", lowered)
    cleaned = re.sub(r"[^\w\s]+", " ", cleaned, flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokenize(value: str) -> list[str]:
    return [token for token in _normalize_text(value).split() if token]


def _stem_token(token: str) -> str:
    if not re.search(r"[а-яё]", token) or len(token) < 5:
        return token
    for suffix in ("ыми", "ими", "ого", "ему", "ами", "ями", "ах", "ях", "ых", "их", "ой", "ей", "ов", "ев", "ом", "ем", "а", "я", "ы", "и"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _token_set(value: str) -> set[str]:
    return {_stem_token(token) for token in _tokenize(value)}


def _parse_vector(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return _parse_vector(parsed)
    return None


def _cosine(left: Any, right: Any) -> float:
    left_vector = _parse_vector(left)
    right_vector = _parse_vector(right)
    if not left_vector or not right_vector or len(left_vector) != len(right_vector):
        return 0.0
    left_norm = sqrt(sum(value * value for value in left_vector))
    right_norm = sqrt(sum(value * value for value in right_vector))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left_vector, right_vector)) / (left_norm * right_norm)


def _is_allowed_tag(tag: str) -> bool:
    return tag in CANONICAL_TAGS and tag not in BROAD_STOP_TAGS


def _build_alias_indexes() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    phrase_index: dict[str, list[str]] = {}
    token_index: dict[str, list[str]] = {}

    for alias, canonical in ALIASES.items():
        if not _is_allowed_tag(canonical):
            continue
        normalized_alias = _normalize_text(alias)
        if not normalized_alias:
            continue
        phrase_index.setdefault(normalized_alias, [])
        _append_unique(phrase_index[normalized_alias], canonical)

        for token in _tokenize(alias):
            if token in TOKEN_STOPWORDS:
                continue
            if len(token) < 4 and token not in {"api", "sql", "css", "html", "js", "ts"}:
                continue
            token_index.setdefault(token, [])
            _append_unique(token_index[token], canonical)

    return phrase_index, token_index


def _find_exact_matches(query: str) -> list[str]:
    phrase_index, token_index = _build_alias_indexes()
    normalized_query = f" {_normalize_text(query)} "
    query_tokens = _token_set(query)
    matches: list[str] = []

    for phrase, tags in phrase_index.items():
        phrase_tokens = _token_set(phrase)
        if f" {phrase} " in normalized_query or (
            len(phrase_tokens) > 1 and phrase_tokens.issubset(query_tokens)
        ):
            for tag in tags:
                _append_unique(matches, tag)

    for token in query_tokens:
        for tag in token_index.get(token, []):
            _append_unique(matches, tag)

    return matches


def load_taxonomy_cache(path: Path = DEFAULT_TAXONOMY_CACHE_PATH) -> dict:
    if not path.exists():
        return {"items": []}
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, dict):
        return payload
    return {"items": []}


def _semantic_matches(
    query_embedding: Any,
    taxonomy_cache: dict,
    *,
    semantic_threshold: float,
    semantic_margin: float,
    max_semantic_tags: int,
) -> tuple[list[dict], float]:
    scores: list[dict] = []
    for item in taxonomy_cache.get("items") or []:
        tag = item.get("tag")
        if not isinstance(tag, str) or not _is_allowed_tag(tag):
            continue
        score = _cosine(query_embedding, item.get("embedding"))
        if score > 0:
            scores.append({"tag": tag, "score": round(score, 6)})

    scores.sort(key=lambda item: item["score"], reverse=True)
    if not scores or scores[0]["score"] < semantic_threshold:
        return [], 0.0

    top_score = scores[0]["score"]
    accepted: list[dict] = []
    for item in scores:
        if item["score"] < semantic_threshold:
            continue
        if item["score"] < top_score - semantic_margin:
            continue
        accepted.append(item)
        if len(accepted) >= max_semantic_tags:
            break
    return accepted, top_score


def _primary_tags(tags: list[str]) -> list[str]:
    area_tags = [
        tag
        for tag in tags
        if TAG_META.get(tag, {}).get("level") == "area"
    ]
    if area_tags:
        return area_tags[:2]
    return tags[:2]


def understand_query(
    query: str,
    query_embedding: Any | None = None,
    *,
    taxonomy_cache: dict | None = None,
    semantic_threshold: float = 0.78,
    semantic_margin: float = 0.08,
    max_semantic_tags: int = 4,
) -> QueryIntent:
    exact_matches = _find_exact_matches(query)
    cache = taxonomy_cache if taxonomy_cache is not None else load_taxonomy_cache()
    semantic_matches, top_score = _semantic_matches(
        query_embedding,
        cache,
        semantic_threshold=semantic_threshold,
        semantic_margin=semantic_margin,
        max_semantic_tags=max_semantic_tags,
    )

    tags: list[str] = []
    for tag in exact_matches:
        _append_unique(tags, tag)
    for match in semantic_matches:
        _append_unique(tags, match["tag"])

    if not tags:
        return _empty_intent()

    confidence = 1.0 if exact_matches else top_score
    return QueryIntent(
        tags=tags,
        primary_tags=_primary_tags(tags),
        confidence=round(confidence, 6),
        exact_matches=exact_matches,
        semantic_matches=semantic_matches,
    )


def build_query_scope(intent: QueryIntent | None) -> set[str]:
    if not intent or not intent.tags:
        return set()

    has_specific_primary = any(tag not in BASE_LANGUAGE_TAGS for tag in intent.primary_tags)
    scope = set(intent.tags)
    for tag in list(scope):
        parent = TAG_META.get(tag, {}).get("parent")
        if parent:
            scope.add(parent)

    for tag, meta in TAG_META.items():
        parent = meta.get("parent")
        if parent and parent in scope and not (has_specific_primary and parent in BASE_LANGUAGE_TAGS):
            scope.add(tag)

    return scope
