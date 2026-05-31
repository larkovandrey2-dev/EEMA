from services.query_understanding import QueryIntent, build_query_scope, understand_query


def test_query_router_uses_taxonomy_embeddings_for_frontend_without_phrase_rules():
    cache = {
        "items": [
            {"tag": "Frontend", "embedding": [1.0, 0.0, 0.0]},
            {"tag": "React", "embedding": [0.96, 0.02, 0.0]},
            {"tag": "Data Analysis", "embedding": [0.0, 1.0, 0.0]},
            {"tag": "Programming", "embedding": [1.0, 0.0, 0.0]},
        ]
    }

    intent = understand_query(
        "нужно изучить фронтенд",
        [1.0, 0.0, 0.0],
        taxonomy_cache=cache,
        semantic_threshold=0.8,
        semantic_margin=0.08,
    )

    assert "Frontend" in intent.tags
    assert "React" in intent.tags
    assert "Programming" not in intent.tags
    assert intent.primary_tags == ["Frontend"]
    assert intent.confidence >= 0.95


def test_query_router_finds_backend_api_by_semantic_taxonomy_matches():
    cache = {
        "items": [
            {"tag": "Backend", "embedding": [0.0, 1.0, 0.0]},
            {"tag": "REST API", "embedding": [0.0, 0.96, 0.0]},
            {"tag": "FastAPI", "embedding": [0.0, 0.94, 0.0]},
            {"tag": "Frontend", "embedding": [1.0, 0.0, 0.0]},
        ]
    }

    intent = understand_query(
        "хочу backend api",
        [0.0, 1.0, 0.0],
        taxonomy_cache=cache,
        semantic_threshold=0.8,
        semantic_margin=0.08,
    )

    assert "Backend" in intent.tags
    assert {"REST API", "FastAPI"} & set(intent.tags)
    assert "Frontend" not in intent.tags


def test_query_router_returns_empty_intent_on_low_confidence():
    cache = {
        "items": [
            {"tag": "Frontend", "embedding": [1.0, 0.0]},
            {"tag": "Backend", "embedding": [0.0, 1.0]},
        ]
    }

    intent = understand_query(
        "что-нибудь интересное",
        [0.5, 0.5],
        taxonomy_cache=cache,
        semantic_threshold=0.9,
    )

    assert intent == QueryIntent(
        tags=[],
        primary_tags=[],
        confidence=0.0,
        exact_matches=[],
        semantic_matches=[],
    )


def test_query_router_handles_russian_inflected_alias_tokens():
    intent = understand_query(
        "хочу питон для анализа данных",
        [0.0, 0.0],
        taxonomy_cache={"items": []},
    )

    assert "Python" in intent.tags
    assert "Data Analysis" in intent.tags
    assert "Business Analysis" not in intent.tags


def test_query_scope_uses_taxonomy_parents_and_children():
    intent = QueryIntent(
        tags=["JavaScript"],
        primary_tags=["JavaScript"],
        confidence=1.0,
        exact_matches=["JavaScript"],
        semantic_matches=[],
    )

    scope = build_query_scope(intent)

    assert "JavaScript" in scope
    assert "React" in scope
    assert "Vue.js" in scope


def test_query_scope_does_not_expand_generic_language_children_when_area_is_primary():
    intent = QueryIntent(
        tags=["Python", "Data Analysis"],
        primary_tags=["Data Analysis"],
        confidence=1.0,
        exact_matches=["Python", "Data Analysis"],
        semantic_matches=[],
    )

    scope = build_query_scope(intent)

    assert "Python" in scope
    assert "Data Analysis" in scope
    assert "FastAPI" not in scope
    assert "Django" not in scope
