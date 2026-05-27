import pytest

from app.api import router_courses
from app.schemas.models import RecommendationInput
from services.query_understanding import QueryIntent


class Response:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, name, fake):
        self.name = name
        self.fake = fake

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def contains(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return Response(self.fake.table_data.get(self.name, []))


class FakeSupabase:
    def __init__(self, match_courses):
        self.table_data = {
            "users": [{"preferences": {"skills": {}, "learning_goals": []}}],
            "courses": [],
        }
        self.match_courses = match_courses
        self.rpc_calls = []

    def table(self, name):
        return FakeTable(name, self)

    def rpc(self, name, params):
        self.rpc_calls.append({"name": name, "params": params})
        if name == "match_courses":
            if isinstance(self.match_courses, list) and self.match_courses and isinstance(self.match_courses[0], list):
                index = min(
                    len([call for call in self.rpc_calls if call["name"] == "match_courses"]) - 1,
                    len(self.match_courses) - 1,
                )
                return RpcBuilder(self.match_courses[index])
            return RpcBuilder(self.match_courses)
        if name == "get_cluster_neighbors":
            return RpcBuilder([])
        raise AssertionError(name)


class RpcBuilder:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return Response(self.data)


def test_advanced_recommendations_do_not_leak_internal_tag_fields(monkeypatch):
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        router_courses,
        "supabase",
        FakeSupabase(
            [
                {
                    "id": 1,
                    "title": "React для начинающих",
                    "url": "https://stepik.org/course/1",
                    "difficulty": "easy",
                    "learners_count": 100,
                    "rating": 4.7,
                    "tags": ["React"],
                    "normalized_tags": ["React"],
                    "raw_tags": ["Информационные технологии", "React"],
                    "tag_meta": {"dropped_tags": ["Информационные технологии"]},
                    "is_paid": False,
                    "price": None,
                    "embedding": [0.1, 0.2],
                    "cluster_id": None,
                    "domain": "it",
                }
            ]
        ),
    )

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="react frontend", limit=1),
        user_id="user-1",
    )

    assert set(result) == {"strategy", "search_query", "main_results", "ml_enrichment"}
    assert set(result["ml_enrichment"]) == {
        "anchor_course_title",
        "cluster_neighbors",
        "markov_roadmap",
        "user_profile",
    }
    course = result["main_results"][0]
    assert course["tags"] == ["React"]
    assert "raw_tags" not in course
    assert "normalized_tags" not in course
    assert "tag_meta" not in course
    assert "domain" not in course


def test_advanced_recommendations_adds_personalization_from_likes(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 10,
                "title": "Python backend",
                "url": "https://stepik.org/course/10",
                "difficulty": "easy",
                "learners_count": 200,
                "rating": 4.5,
                "tags": ["Python", "Django"],
                "is_paid": False,
                "price": None,
                "embedding": [0.0, 1.0],
                "cluster_id": 8,
                "similarity": 0.7,
            },
            {
                "id": 11,
                "title": "Python для анализа данных",
                "url": "https://stepik.org/course/11",
                "difficulty": "easy",
                "learners_count": 100,
                "rating": 4.5,
                "tags": ["Python", "Pandas"],
                "is_paid": False,
                "price": None,
                "embedding": [1.0, 0.0],
                "cluster_id": 4,
                "similarity": 0.6,
            },
        ]
    )
    fake_supabase.table_data["user_likes"] = [{"course_id": 99}]
    fake_supabase.table_data["courses"] = [
        {
            "id": 99,
            "title": "Pandas liked",
            "tags": ["Python", "Pandas"],
            "embedding": [1.0, 0.0],
            "cluster_id": 4,
        }
    ]
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        router_courses,
        "understand_query",
        lambda query, query_embedding: QueryIntent(
            tags=["Python", "Pandas", "Data Analysis"],
            primary_tags=["Data Analysis"],
            confidence=0.95,
            exact_matches=["Python"],
            semantic_matches=[{"tag": "Data Analysis", "score": 0.95}],
        ),
    )
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="хочу изучить питон", limit=2),
        user_id="user-1",
    )

    assert result["main_results"][0]["title"] == "Python для анализа данных"
    assert result["main_results"][0]["personalization"]["matched_tags"] == ["Python", "Pandas"]
    assert result["main_results"][0]["reason"] == "Похоже на ваши лайкнутые курсы по тегам: Python, Pandas"
    assert result["ml_enrichment"]["user_profile"]["active"] is True
    assert result["ml_enrichment"]["user_profile"]["liked_courses_count"] == 1
    assert result["ml_enrichment"]["user_profile"]["top_tags"] == ["Python", "Pandas"]
    assert result["ml_enrichment"]["user_profile"]["query_intent_tags"] == [
        "Python",
        "Pandas",
        "Data Analysis",
    ]


def test_advanced_recommendations_cleans_broad_tags_from_personalization(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 10,
                "title": "Python в Minecraft",
                "url": "https://stepik.org/course/10",
                "difficulty": "easy",
                "learners_count": 200,
                "rating": 4.5,
                "tags": ["Информационные технологии", "Языки программирования", "Python", "Minecraft"],
                "is_paid": False,
                "price": None,
                "embedding": "[0.0, 1.0]",
                "cluster_id": 4,
                "similarity": 0.7,
            },
            {
                "id": 11,
                "title": "Python для анализа данных",
                "url": "https://stepik.org/course/11",
                "difficulty": "easy",
                "learners_count": 100,
                "rating": 4.5,
                "tags": ["Python", "Pandas", "Data Analysis"],
                "is_paid": False,
                "price": None,
                "embedding": "[1.0, 0.0]",
                "cluster_id": 4,
                "similarity": 0.6,
            },
        ]
    )
    fake_supabase.table_data["user_likes"] = [{"course_id": 99}]
    fake_supabase.table_data["courses"] = [
        {
            "id": 99,
            "title": "Liked dirty data course",
            "tags": ["Информационные технологии", "Python", "Pandas", "Data Analysis"],
            "embedding": "[1.0, 0.0]",
            "cluster_id": 4,
        }
    ]
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        router_courses,
        "understand_query",
        lambda query, query_embedding: QueryIntent(
            tags=["Python", "Pandas", "Data Analysis"],
            primary_tags=["Data Analysis"],
            confidence=0.95,
            exact_matches=["Python"],
            semantic_matches=[{"tag": "Data Analysis", "score": 0.95}],
        ),
    )
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="хочу питон для анализа данных", limit=2),
        user_id="user-1",
    )

    assert result["main_results"][0]["title"] == "Python для анализа данных"
    assert "Информационные технологии" not in result["main_results"][0]["reason"]
    assert "Информационные технологии" not in result["main_results"][0]["personalization"]["matched_tags"]
    assert result["ml_enrichment"]["user_profile"]["top_tags"] == ["Python", "Pandas", "Data Analysis"]


def test_advanced_recommendations_retry_with_relaxed_threshold_when_rag_is_empty(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            [],
            [
                {
                    "id": 1,
                    "title": "Python быстро",
                    "url": "https://stepik.org/course/1",
                    "difficulty": "easy",
                    "learners_count": 100,
                    "rating": 4.7,
                    "tags": ["Python"],
                    "is_paid": False,
                    "price": None,
                    "embedding": [0.1, 0.2],
                    "cluster_id": None,
                }
            ],
        ]
    )
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        router_courses,
        "understand_query",
        lambda query, query_embedding: QueryIntent(
            tags=["Python"],
            primary_tags=["Python"],
            confidence=1.0,
            exact_matches=["Python"],
            semantic_matches=[],
        ),
    )
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="просто хочу изучить питон", limit=1),
        user_id="user-1",
    )

    match_thresholds = [
        call["params"]["match_threshold"]
        for call in fake_supabase.rpc_calls
        if call["name"] == "match_courses"
    ]
    assert match_thresholds == [0.55, 0.45]
    assert result["main_results"][0]["title"] == "Python быстро"


def test_basic_python_query_does_not_build_ml_markov_from_generic_tag(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 1,
                "title": "Python с нуля",
                "url": "https://stepik.org/course/1",
                "difficulty": "easy",
                "learners_count": 100,
                "rating": 4.7,
                "tags": ["Информационные технологии", "Языки программирования", "Python"],
                "is_paid": False,
                "price": None,
                "embedding": [0.1, 0.2],
                "cluster_id": None,
            }
        ]
    )
    fake_supabase.table_data["courses"] = [
        {
            "id": 99,
            "title": "Machine Learning next",
            "url": "https://stepik.org/course/99",
            "difficulty": "easy",
            "learners_count": 1000,
            "tags": ["Machine Learning"],
        }
    ]
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {"Python": {"Machine Learning": 1.0}})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        router_courses,
        "understand_query",
        lambda query, query_embedding: QueryIntent(
            tags=["Python"],
            primary_tags=["Python"],
            confidence=1.0,
            exact_matches=["Python"],
            semantic_matches=[],
        ),
    )
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="Надо в питоне прокачаться", limit=1),
        user_id="user-1",
    )

    assert result["ml_enrichment"]["markov_roadmap"] == []


def test_data_query_uses_data_intent_before_generic_python_for_markov(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 1,
                "title": "Python для анализа данных",
                "url": "https://stepik.org/course/1",
                "difficulty": "easy",
                "learners_count": 100,
                "rating": 4.7,
                "tags": ["Информационные технологии", "Python", "Data Analysis"],
                "is_paid": False,
                "price": None,
                "embedding": [0.1, 0.2],
                "cluster_id": None,
            }
        ]
    )
    fake_supabase.table_data["courses"] = [
        {
            "id": 99,
            "title": "Pandas next",
            "url": "https://stepik.org/course/99",
            "difficulty": "easy",
            "learners_count": 1000,
            "tags": ["Pandas"],
        }
    ]
    monkeypatch.setattr(
        router_courses,
        "MARKOV_MATRIX",
        {"Python": {"Machine Learning": 1.0}, "Data Analysis": {"Pandas": 1.0}},
    )
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        router_courses,
        "understand_query",
        lambda query, query_embedding: QueryIntent(
            tags=["Python", "Data Analysis"],
            primary_tags=["Data Analysis"],
            confidence=0.95,
            exact_matches=["Python"],
            semantic_matches=[{"tag": "Data Analysis", "score": 0.95}],
        ),
    )
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="хочу питон для анализа данных", limit=1),
        user_id="user-1",
    )

    assert result["ml_enrichment"]["markov_roadmap"][0]["markov_reason"] == (
        "Логичный следующий шаг (Тема: Pandas)"
    )


def test_router_markov_next_tags_drop_broad_targets(monkeypatch):
    monkeypatch.setattr(
        router_courses,
        "MARKOV_MATRIX",
        {"Data Analysis": {"Информационные технологии": 0.9, "Pandas": 0.1}},
    )

    assert router_courses.get_markov_next_tags(["Data Analysis"], top_k=2) == ["Pandas"]


def test_frontend_api_uses_context_relevant_react_like(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 10,
                "title": "Frontend React практика",
                "url": "https://stepik.org/course/10",
                "difficulty": "easy",
                "learners_count": 200,
                "rating": 4.5,
                "tags": ["Frontend", "React", "Web Development"],
                "is_paid": False,
                "price": None,
                "embedding": [0.0, 1.0],
                "cluster_id": 4,
                "similarity": 0.55,
            },
            {
                "id": 11,
                "title": "Machine Learning старт",
                "url": "https://stepik.org/course/11",
                "difficulty": "easy",
                "learners_count": 100,
                "rating": 4.5,
                "tags": ["Machine Learning", "Deep Learning"],
                "is_paid": False,
                "price": None,
                "embedding": [1.0, 0.0],
                "cluster_id": 9,
                "similarity": 0.9,
            },
        ]
    )
    fake_supabase.table_data["user_likes"] = [{"course_id": 90}, {"course_id": 91}]
    fake_supabase.table_data["courses"] = [
        {
            "id": 90,
            "title": "Data liked",
            "tags": ["Data Analytics", "Machine Learning", "Deep Learning"],
            "embedding": [1.0, 0.0],
            "cluster_id": 9,
        },
        {
            "id": 91,
            "title": "React liked",
            "tags": ["Frontend", "React", "Web Development"],
            "embedding": [0.0, 1.0],
            "cluster_id": 4,
        },
    ]
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.0, 1.0])
    monkeypatch.setattr(
        router_courses,
        "understand_query",
        lambda query, query_embedding: QueryIntent(
            tags=["Frontend", "React"],
            primary_tags=["Frontend"],
            confidence=0.96,
            exact_matches=[],
            semantic_matches=[{"tag": "Frontend", "score": 0.96}],
        ),
    )
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="нужно изучить фронтенд", limit=2),
        user_id="user-1",
    )

    assert result["main_results"][0]["id"] == 10
    assert result["main_results"][0]["reason"] == "Похоже на ваши лайкнутые курсы по тегам: Frontend, React"
    assert result["main_results"][1]["personalization"]["matched_tags"] == []
    assert result["main_results"][1]["personalization"]["embedding_similarity"] == 0.0
    assert result["ml_enrichment"]["user_profile"]["query_intent_tags"] == ["Frontend", "React"]
    assert result["ml_enrichment"]["user_profile"]["query_matched_liked_tags"] == [
        "Frontend",
        "React",
    ]
    assert result["ml_enrichment"]["user_profile"]["context_liked_courses_count"] == 1


@pytest.mark.parametrize("saved_level", ["Advanced", "high"])
def test_advanced_recommendations_do_not_return_easy_matching_skill_for_high_user_level(
    monkeypatch,
    saved_level,
):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 1,
                "title": "Python easy",
                "url": "https://stepik.org/course/1",
                "difficulty": "easy",
                "learners_count": 10,
                "rating": 4.0,
                "tags": ["Python"],
                "is_paid": False,
                "price": None,
                "embedding": [0.1, 0.2],
                "cluster_id": None,
                "similarity": 0.9,
            }
        ]
    )
    fake_supabase.table_data["users"] = [
        {"preferences": {"skills": {"Python": saved_level}, "learning_goals": []}}
    ]
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="Python", limit=1),
        user_id="user-1",
    )

    assert result["main_results"] == []


def test_advanced_recommendations_normalizes_profile_alias_and_allows_normal_course(monkeypatch):
    fake_supabase = FakeSupabase(
        [
            {
                "id": 1,
                "title": "Python easy",
                "url": "https://stepik.org/course/1",
                "difficulty": "easy",
                "tags": ["Python"],
                "embedding": [0.1, 0.2],
                "cluster_id": None,
            },
            {
                "id": 2,
                "title": "Python normal",
                "url": "https://stepik.org/course/2",
                "difficulty": "normal",
                "tags": ["Python"],
                "embedding": [0.1, 0.2],
                "cluster_id": None,
            },
        ]
    )
    fake_supabase.table_data["users"] = [
        {"preferences": {"skills": {"питон": "high"}, "learning_goals": []}}
    ]
    monkeypatch.setattr(router_courses, "MARKOV_MATRIX", {})
    monkeypatch.setattr(router_courses, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_advanced_recommendations(
        RecommendationInput(query="Python", limit=2),
        user_id="user-1",
    )

    assert [course["id"] for course in result["main_results"]] == [2]


def test_baseline_filters_easy_course_for_high_matching_skill(monkeypatch):
    fake_supabase = FakeSupabase([])
    fake_supabase.table_data["users"] = [
        {"preferences": {"skills": {"Python": "Advanced"}, "learning_goals": []}}
    ]
    fake_supabase.table_data["courses"] = [
        {
            "id": 1,
            "title": "Python easy",
            "url": "https://stepik.org/course/1",
            "difficulty": "easy",
            "tags": ["Python"],
            "learners_count": 20,
        },
        {
            "id": 2,
            "title": "Python hard",
            "url": "https://stepik.org/course/2",
            "difficulty": "hard",
            "tags": ["Python"],
            "learners_count": 10,
        },
    ]
    monkeypatch.setattr(router_courses, "supabase", fake_supabase)

    result = router_courses.get_recommend_baseline(user_id="user-1", limit=10)

    assert [course["id"] for course in result["courses"]] == [2]
