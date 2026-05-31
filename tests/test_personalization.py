from services.personalization import (
    build_user_interest_profile,
    cosine_similarity,
    get_scoring_tags,
    personalize_courses,
)
from services.query_understanding import QueryIntent


def test_profile_counts_liked_tags_clusters_and_centroid():
    liked_courses = [
        {"id": 1, "tags": ["Python", "Pandas"], "cluster_id": 7, "embedding": [1.0, 0.0]},
        {"id": 2, "tags": ["Python", "SQL"], "cluster_id": 7, "embedding": [0.0, 1.0]},
    ]

    profile = build_user_interest_profile(liked_courses)

    assert profile["active"] is True
    assert profile["liked_course_ids"] == {1, 2}
    assert profile["tag_counts"]["Python"] == 2
    assert profile["top_tags"] == ["Python", "Pandas", "SQL"]
    assert profile["liked_cluster_ids"] == {7}
    assert profile["liked_embedding_centroid"] == [0.5, 0.5]


def test_scoring_tags_remove_broad_legacy_tags_and_normalize_specific_tags():
    course = {
        "tags": [
            "Информационные технологии",
            "Языки программирования",
            "Programming",
            "Python",
            "Pandas",
            "Data Analysis",
        ]
    }

    assert get_scoring_tags(course) == ["Python", "Pandas", "Data Analysis"]


DATA_INTENT = QueryIntent(
    tags=["Python", "Data Analysis", "Pandas"],
    primary_tags=["Data Analysis"],
    confidence=0.95,
    exact_matches=["Python"],
    semantic_matches=[{"tag": "Data Analysis", "score": 0.95}],
)

FRONTEND_INTENT = QueryIntent(
    tags=["Frontend", "React"],
    primary_tags=["Frontend"],
    confidence=0.96,
    exact_matches=[],
    semantic_matches=[{"tag": "Frontend", "score": 0.96}],
)


def test_personalize_courses_boosts_matching_tags_and_penalizes_liked_courses():
    profile = build_user_interest_profile(
        [
            {"id": 1, "tags": ["Python", "Pandas"], "cluster_id": 4, "embedding": [1.0, 0.0]},
        ],
        query_intent=DATA_INTENT,
    )
    candidates = [
        {
            "id": 10,
            "title": "Python для анализа данных",
            "tags": ["Python", "Pandas"],
            "cluster_id": 4,
            "embedding": [1.0, 0.0],
            "similarity": 0.4,
            "learners_count": 10,
            "rating": 0,
        },
        {
            "id": 11,
            "title": "Python backend",
            "tags": ["Python", "Django"],
            "cluster_id": 8,
            "embedding": [0.0, 1.0],
            "similarity": 0.5,
            "learners_count": 1000,
            "rating": 0,
        },
        {
            "id": 1,
            "title": "Already liked",
            "tags": ["Python", "Pandas"],
            "cluster_id": 4,
            "embedding": [1.0, 0.0],
            "similarity": 0.9,
            "learners_count": 1000,
            "rating": 5,
        },
    ]

    ranked = personalize_courses(candidates, profile, query_intent=DATA_INTENT, user_skills={}, limit=3)

    assert [course["id"] for course in ranked] == [10, 11, 1]
    assert ranked[0]["personalization"]["matched_tags"] == ["Python", "Pandas"]
    assert ranked[0]["personalization"]["same_cluster"] is True
    assert ranked[0]["personalization"]["already_liked"] is False
    assert ranked[0]["reason"] == "Похоже на ваши лайкнутые курсы по тегам: Python, Pandas"
    assert ranked[-1]["personalization"]["already_liked"] is True


def test_data_query_ranks_data_course_above_minecraft_with_dirty_legacy_tags():
    profile = build_user_interest_profile(
        [
            {
                "id": 1,
                "tags": [
                    "Информационные технологии",
                    "Python",
                    "Data Analysis",
                    "Pandas",
                ],
                "cluster_id": 4,
                "embedding": "[1.0, 0.0]",
            }
        ],
        query_intent=DATA_INTENT,
    )
    candidates = [
        {
            "id": 10,
            "title": "Python в Minecraft",
            "tags": [
                "Game Development",
                "Языки программирования",
                "Minecraft",
                "Python",
                "Информационные технологии",
            ],
            "cluster_id": 4,
            "embedding": "[0.0, 1.0]",
            "similarity": 0.7,
        },
        {
            "id": 11,
            "title": "Python для анализа данных",
            "tags": ["Python", "Pandas", "Data Analysis"],
            "cluster_id": 4,
            "embedding": "[1.0, 0.0]",
            "similarity": 0.6,
        },
    ]

    ranked = personalize_courses(
        candidates,
        profile,
        query_intent=DATA_INTENT,
        user_skills={},
        limit=2,
    )

    assert ranked[0]["id"] == 11
    assert ranked[0]["personalization"]["matched_tags"] == ["Python", "Pandas", "Data Analysis"]
    assert "Информационные технологии" not in ranked[0]["reason"]
    assert ranked[0]["personalization"]["score"] <= 2.5
    assert ranked[1]["personalization"]["matched_tags"] == ["Python"]


def test_same_cluster_without_meaningful_match_does_not_boost_course():
    profile = build_user_interest_profile(
        [{"id": 1, "tags": ["Deep Learning"], "cluster_id": 9, "embedding": [1.0, 0.0]}],
        query_intent=DATA_INTENT,
    )
    candidates = [
        {
            "id": 10,
            "title": "Same cluster but unrelated",
            "tags": ["Python"],
            "cluster_id": 9,
            "embedding": [0.0, 1.0],
            "similarity": 0.5,
        }
    ]

    ranked = personalize_courses(candidates, profile, query_intent=DATA_INTENT, user_skills={}, limit=1)

    assert ranked[0]["personalization"]["same_cluster"] is False
    assert ranked[0]["personalization"]["score"] == 0.0


def test_generic_python_only_gets_small_soft_boost():
    profile = build_user_interest_profile(
        [{"id": 1, "tags": ["Python"], "cluster_id": 4, "embedding": [1.0, 0.0]}],
        query_intent=QueryIntent(
            tags=["Python"],
            primary_tags=["Python"],
            confidence=1.0,
            exact_matches=["Python"],
            semantic_matches=[],
        ),
    )
    candidates = [
        {
            "id": 10,
            "title": "Python с нуля",
            "tags": ["Информационные технологии", "Python"],
            "cluster_id": 4,
            "embedding": [0.0, 1.0],
            "similarity": 0.5,
        }
    ]

    ranked = personalize_courses(
        candidates,
        profile,
        query_intent=QueryIntent(
            tags=["Python"],
            primary_tags=["Python"],
            confidence=1.0,
            exact_matches=["Python"],
            semantic_matches=[],
        ),
        user_skills={},
        limit=1,
    )

    assert ranked[0]["personalization"]["matched_tags"] == ["Python"]
    assert ranked[0]["personalization"]["score"] <= 1.0
    assert ranked[0]["reason"] == "Подходит под запрос по Python"


def test_personalize_courses_without_likes_keeps_semantic_order_and_adds_reason():
    profile = build_user_interest_profile([])
    candidates = [
        {"id": 1, "title": "Low", "tags": ["Python"], "similarity": 0.1},
        {"id": 2, "title": "High", "tags": ["Python"], "similarity": 0.9},
    ]

    ranked = personalize_courses(candidates, profile, query_intent=DATA_INTENT, user_skills={}, limit=2)

    assert [course["id"] for course in ranked] == [2, 1]
    assert ranked[0]["reason"] == "Подходит под запрос по тегам: Python"
    assert ranked[0]["personalization"]["score"] == 0.0
    assert ranked[0]["personalization"]["query_tags"] == ["Python", "Data Analysis", "Pandas"]


def test_cosine_similarity_handles_missing_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity("[1.0, 0.0]", [1.0, 0.0]) == 1.0
    assert cosine_similarity([], [1.0, 0.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_frontend_query_uses_only_context_relevant_likes_for_centroid_and_reason():
    profile = build_user_interest_profile(
        [
            {
                "id": 1,
                "tags": ["Data Analytics", "Machine Learning", "Deep Learning"],
                "cluster_id": 9,
                "embedding": [1.0, 0.0],
            },
            {
                "id": 2,
                "tags": ["React", "Frontend", "Web Development"],
                "cluster_id": 4,
                "embedding": [0.0, 1.0],
            },
        ],
        query_intent=FRONTEND_INTENT,
    )
    candidates = [
        {
            "id": 10,
            "title": "Frontend React практика",
            "tags": ["React", "Frontend", "Web Development"],
            "cluster_id": 4,
            "embedding": [0.0, 1.0],
            "similarity": 0.55,
        },
        {
            "id": 11,
            "title": "Machine Learning с нуля",
            "tags": ["Machine Learning", "Deep Learning"],
            "cluster_id": 9,
            "embedding": [1.0, 0.0],
            "similarity": 0.9,
        },
    ]

    ranked = personalize_courses(candidates, profile, query_intent=FRONTEND_INTENT, user_skills={}, limit=2)

    assert profile["context_liked_courses_count"] == 1
    assert profile["query_matched_liked_tags"] == ["React", "Frontend"]
    assert ranked[0]["id"] == 10
    assert ranked[0]["reason"] == "Похоже на ваши лайкнутые курсы по тегам: React, Frontend"
    assert ranked[1]["personalization"]["matched_tags"] == []
    assert ranked[1]["personalization"]["embedding_similarity"] == 0.0


def test_data_query_does_not_treat_backend_python_children_as_context_likes():
    profile = build_user_interest_profile(
        [
            {
                "id": 1,
                "tags": ["Python", "FastAPI", "Backend"],
                "cluster_id": 8,
                "embedding": [1.0, 0.0],
            },
            {
                "id": 2,
                "tags": ["Python", "Pandas", "Data Analysis"],
                "cluster_id": 4,
                "embedding": [0.0, 1.0],
            },
        ],
        query_intent=DATA_INTENT,
    )

    assert profile["context_liked_courses_count"] == 1
    assert profile["query_matched_liked_tags"] == ["Python", "Pandas", "Data Analysis"]
    assert "FastAPI" not in profile["query_matched_liked_tags"]


def test_query_only_match_does_not_claim_liked_reason():
    profile = build_user_interest_profile(
        [
            {
                "id": 1,
                "tags": ["Data Analysis", "Machine Learning"],
                "cluster_id": 9,
                "embedding": [1.0, 0.0],
            }
        ],
        query_intent=FRONTEND_INTENT,
    )
    candidates = [
        {
            "id": 10,
            "title": "Frontend основы",
            "tags": ["Frontend"],
            "cluster_id": 4,
            "embedding": [0.0, 1.0],
            "similarity": 0.8,
        }
    ]

    ranked = personalize_courses(candidates, profile, query_intent=FRONTEND_INTENT, user_skills={}, limit=1)

    assert ranked[0]["personalization"]["matched_tags"] == []
    assert ranked[0]["reason"] == "Подходит под запрос по тегам: Frontend"
