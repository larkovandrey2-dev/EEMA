from ML.scripts.difficulty_prediction import DifficultyPrediction
from data_pipeline import pipeline as pipeline_module
from data_pipeline.pipeline import (
    SupabaseCourseRepository,
    apply_manual_holdout_labels,
    backfill_missing_difficulty,
    build_course_payload,
    build_embedding_text,
    build_taxonomy_embedding_cache,
    needs_embedding,
    reserve_manual_holdout_rows,
)
from data_pipeline.stepik_client import StepikClient
from data_pipeline.tag_normalizer import normalize_tags


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if url.endswith("/api/tags"):
            return FakeResponse(
                {
                    "tags": [
                        {"id": 10, "title": "Python"},
                        {"id": 11, "title": "Pandas"},
                    ]
                }
            )
        return FakeResponse({"courses": [], "meta": {"has_next": False}})


def test_stepik_client_fetches_tags_in_one_batch_with_ids_array():
    session = FakeSession()
    client = StepikClient(session=session)

    tags = client.fetch_tags_by_ids([10, 11, 10])

    assert tags == {10: "Python", 11: "Pandas"}
    assert len(session.calls) == 1
    assert session.calls[0]["url"].endswith("/api/tags")
    assert session.calls[0]["params"] == {"ids[]": [10, 11]}


def test_build_course_payload_keeps_raw_and_normalized_tags_compatible():
    course = {
        "id": 123,
        "title": "Pandas для анализа данных",
        "summary": "Практический курс по pandas",
        "learners_count": 100,
        "difficulty": "easy",
        "average_score": 4.8,
        "workload": "10 hours",
        "is_paid": False,
        "price": None,
    }

    payload = build_course_payload(
        course,
        raw_tags=["Информационные технологии", "Python", "Pandas"],
        normalize=normalize_tags,
    )

    assert payload["stepik_id"] == 123
    assert payload["raw_tags"] == ["Информационные технологии", "Python", "Pandas"]
    assert payload["normalized_tags"] == ["Python", "Pandas"]
    assert payload["tags"] == ["Python", "Pandas"]
    assert payload["domain"] == "it"
    assert payload["tag_meta"]["dropped_tags"] == ["Информационные технологии"]
    assert payload["tag_meta"]["difficulty_meta"]["source"] == "stepik"
    assert "embedding_source_hash" in payload["tag_meta"]


class FakeDifficultyPredictor:
    def predict(self, course):
        return DifficultyPrediction(
            level="normal",
            confidence=0.81,
            model_version="difficulty-v1",
        )


class FakeSelectiveDifficultyPredictor:
    def predict(self, course):
        if course.get("title") == "No safe prediction":
            return None
        return DifficultyPrediction(
            level="normal",
            confidence=0.91,
            model_version="selective-v1",
            strategy="selective_easy_normal",
        )


def test_build_course_payload_predicts_missing_stepik_difficulty_before_embedding_hash():
    payload = build_course_payload(
        {"id": 124, "title": "API design", "summary": "Build an API", "difficulty": None},
        raw_tags=["FastAPI"],
        difficulty_predictor=FakeDifficultyPredictor(),
    )

    assert payload["difficulty"] == "normal"
    assert payload["tag_meta"]["difficulty_meta"] == {
        "source": "model",
        "model_version": "difficulty-v1",
        "confidence": 0.81,
        "predicted_at": payload["tag_meta"]["difficulty_meta"]["predicted_at"],
    }
    assert "Difficulty: normal" in build_embedding_text(payload)


def test_build_course_payload_leaves_missing_difficulty_null_when_selective_model_abstains():
    payload = build_course_payload(
        {"id": 128, "title": "No safe prediction", "summary": "", "difficulty": None},
        raw_tags=["Python"],
        difficulty_predictor=FakeSelectiveDifficultyPredictor(),
    )

    assert payload["difficulty"] is None
    assert "difficulty_meta" not in payload["tag_meta"]


def test_stepik_difficulty_overrides_model_value_and_existing_manual_value_is_preserved():
    model_row = {
        "difficulty": "normal",
        "tag_meta": {"difficulty_meta": {"source": "model", "model_version": "old"}},
    }
    payload = build_course_payload(
        {"id": 125, "title": "Deep API", "summary": "", "difficulty": "hard"},
        raw_tags=["FastAPI"],
        existing_row=model_row,
        difficulty_predictor=FakeDifficultyPredictor(),
    )
    assert payload["difficulty"] == "hard"
    assert payload["tag_meta"]["difficulty_meta"]["source"] == "stepik"

    manual_row = {
        "difficulty": "hard",
        "tag_meta": {"difficulty_meta": {"source": "manual_holdout"}},
    }
    payload = build_course_payload(
        {"id": 126, "title": "Manual", "summary": "", "difficulty": None},
        raw_tags=["Python"],
        existing_row=manual_row,
        difficulty_predictor=FakeDifficultyPredictor(),
    )
    assert payload["difficulty"] == "hard"
    assert payload["tag_meta"]["difficulty_meta"]["source"] == "manual_holdout"

    pending_row = {
        "difficulty": None,
        "tag_meta": {"difficulty_meta": {"source": "manual_holdout"}},
    }
    payload = build_course_payload(
        {"id": 127, "title": "Reserved", "summary": "", "difficulty": None},
        raw_tags=["Python"],
        existing_row=pending_row,
        difficulty_predictor=FakeDifficultyPredictor(),
    )
    assert payload["difficulty"] is None
    assert payload["tag_meta"]["difficulty_meta"]["source"] == "manual_holdout"


def test_needs_embedding_only_when_source_hash_changes_or_vector_missing():
    payload = {"tag_meta": {"embedding_source_hash": "new-hash"}}

    assert needs_embedding(None, payload) is True
    assert needs_embedding({"embedding": None, "tag_meta": {"embedding_source_hash": "new-hash"}}, payload) is True
    assert needs_embedding({"embedding": [0.1], "tag_meta": {"embedding_source_hash": "old-hash"}}, payload) is True
    assert needs_embedding({"embedding": [0.1], "tag_meta": {"embedding_source_hash": "new-hash"}}, payload) is False


def test_backfill_updates_only_missing_difficulty_and_regenerates_embedding():
    updates = []
    rows = [
        {
            "id": 1,
            "title": "Unlabelled API",
            "summary": "",
            "difficulty": None,
            "normalized_tags": ["FastAPI"],
            "tags": ["FastAPI"],
            "tag_meta": {"workload": "3 hours"},
        },
        {
            "id": 3,
            "title": "Reserved for review",
            "difficulty": None,
            "normalized_tags": ["Python"],
            "tag_meta": {"difficulty_meta": {"source": "manual_holdout"}},
        },
        {"id": 2, "difficulty": "easy", "tag_meta": {}},
    ]

    count = backfill_missing_difficulty(
        rows,
        predictor=FakeDifficultyPredictor(),
        update_course=lambda course_id, fields: updates.append((course_id, fields)),
        embed_fn=lambda text: [float("Difficulty: normal" in text)],
    )

    assert count == 1
    assert updates[0][0] == 1
    assert updates[0][1]["difficulty"] == "normal"
    assert updates[0][1]["embedding"] == [1.0]
    assert updates[0][1]["tag_meta"]["difficulty_meta"]["source"] == "model"
    assert "embedding_source_hash" in updates[0][1]["tag_meta"]


def test_selective_backfill_records_strategy_and_does_not_embed_abstentions():
    updates = []
    rows = [
        {"id": 1, "title": "Safe normal", "difficulty": None, "tag_meta": {}},
        {"id": 2, "title": "No safe prediction", "difficulty": None, "tag_meta": {}},
    ]

    count = backfill_missing_difficulty(
        rows,
        predictor=FakeSelectiveDifficultyPredictor(),
        update_course=lambda course_id, fields: updates.append((course_id, fields)),
        embed_fn=lambda text: [1.0],
    )

    assert count == 1
    assert [course_id for course_id, _ in updates] == [1]
    assert updates[0][1]["tag_meta"]["difficulty_meta"]["strategy"] == "selective_easy_normal"


def test_loading_difficulty_predictor_prefers_strict_active_model(monkeypatch):
    monkeypatch.setattr(pipeline_module, "load_active_predictor", lambda: "strict")
    monkeypatch.setattr(pipeline_module, "load_active_selective_predictor", lambda: "selective")

    assert pipeline_module.load_difficulty_predictor() == "strict"


class FakeDifficultyRepository:
    def __init__(self, rows):
        self.rows = {row["id"]: row for row in rows}
        self.updates = []

    def get_course_by_id(self, course_id):
        return self.rows.get(course_id)

    def update_course(self, course_id, fields):
        self.updates.append((course_id, fields))
        self.rows[course_id] = {**self.rows[course_id], **fields}


class FakeSupabaseQuery:
    def __init__(self):
        self.selected_fields = None

    def select(self, fields):
        self.selected_fields = fields
        return self

    def is_(self, field, value):
        return self

    def range(self, start, end):
        return self

    def execute(self):
        return type("Response", (), {"data": []})()


class FakeSupabase:
    def __init__(self):
        self.query = FakeSupabaseQuery()

    def table(self, name):
        assert name == "courses"
        return self.query


def test_difficulty_repository_does_not_download_embeddings_for_export_or_training():
    supabase = FakeSupabase()
    repository = SupabaseCourseRepository(supabase)

    repository.iter_courses_for_difficulty(only_missing=True)

    assert "embedding" not in supabase.query.selected_fields.split(", ")


def test_manual_holdout_fills_missing_row_but_does_not_overwrite_stepik_value():
    repository = FakeDifficultyRepository(
        [
            {
                "id": 1,
                "title": "Needs label",
                "difficulty": None,
                "normalized_tags": ["Python"],
                "tag_meta": {},
            },
            {
                "id": 2,
                "title": "Known",
                "difficulty": "easy",
                "normalized_tags": ["Python"],
                "tag_meta": {"difficulty_meta": {"source": "stepik"}},
            },
        ]
    )

    count = apply_manual_holdout_labels(
        [
            {"id": 1, "manual_difficulty": "hard"},
            {"id": 2, "manual_difficulty": "hard"},
        ],
        repository=repository,
        embed_fn=lambda text: [1.0],
    )

    assert count == 1
    assert repository.updates[0][0] == 1
    assert repository.updates[0][1]["difficulty"] == "hard"
    assert repository.updates[0][1]["tag_meta"]["difficulty_meta"]["source"] == "manual_holdout"

    repeated = apply_manual_holdout_labels(
        [{"id": 1, "manual_difficulty": "hard"}],
        repository=repository,
        embed_fn=lambda text: [1.0],
    )
    assert repeated == 0


def test_export_reservation_marks_selected_null_rows_as_manual_holdout():
    updates = []
    count = reserve_manual_holdout_rows(
        [
            {"id": 2, "difficulty": "easy", "tag_meta": {}},
            {"id": 1, "difficulty": None, "tag_meta": {"workload": "2 hours"}},
        ],
        size=10,
        update_course=lambda course_id, fields: updates.append((course_id, fields)),
    )

    assert count == 1
    assert updates == [
        (
            1,
            {
                "tag_meta": {
                    "workload": "2 hours",
                    "difficulty_meta": {"source": "manual_holdout"},
                }
            },
        )
    ]

    existing_holdout_updates = []
    count = reserve_manual_holdout_rows(
        [
            {"id": 1, "difficulty": None, "tag_meta": {}},
            {"id": 3, "difficulty": None, "tag_meta": {}},
        ],
        size=10,
        reserved_ids={3},
        update_course=lambda course_id, fields: existing_holdout_updates.append((course_id, fields)),
    )
    assert count == 1
    assert existing_holdout_updates[0][0] == 3


def test_taxonomy_cache_builds_records_from_canonical_tags(tmp_path):
    output_path = tmp_path / "taxonomy_embeddings.json"

    count = build_taxonomy_embedding_cache(
        output_path=output_path,
        embed_fn=lambda text: [float("Frontend" in text), float("React" in text)],
        tags=["Frontend", "React"],
        request_delay_seconds=0.0,
    )

    assert count == 2
    payload = output_path.read_text(encoding="utf-8")
    assert "Frontend" in payload
    assert "React" in payload
    assert "text-search-doc" in payload


def test_taxonomy_cache_retries_yandex_rate_limit_errors(tmp_path):
    output_path = tmp_path / "taxonomy_embeddings.json"
    calls = []
    sleeps = []

    def flaky_embed(text):
        calls.append(text)
        if len(calls) == 1:
            raise RuntimeError("Yandex embedding API error 429: quota limit exceed")
        return [1.0, 0.0]

    count = build_taxonomy_embedding_cache(
        output_path=output_path,
        embed_fn=flaky_embed,
        tags=["Frontend"],
        request_delay_seconds=0.0,
        sleep_fn=sleeps.append,
    )

    assert count == 1
    assert len(calls) == 2
    assert sleeps == [1.0]
