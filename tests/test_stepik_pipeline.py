from data_pipeline.pipeline import build_course_payload, build_taxonomy_embedding_cache, needs_embedding
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
    assert "embedding_source_hash" in payload["tag_meta"]


def test_needs_embedding_only_when_source_hash_changes_or_vector_missing():
    payload = {"tag_meta": {"embedding_source_hash": "new-hash"}}

    assert needs_embedding(None, payload) is True
    assert needs_embedding({"embedding": None, "tag_meta": {"embedding_source_hash": "new-hash"}}, payload) is True
    assert needs_embedding({"embedding": [0.1], "tag_meta": {"embedding_source_hash": "old-hash"}}, payload) is True
    assert needs_embedding({"embedding": [0.1], "tag_meta": {"embedding_source_hash": "new-hash"}}, payload) is False


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
