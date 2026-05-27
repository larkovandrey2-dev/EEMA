from data_pipeline.audit import compute_audit_metrics


def test_audit_reports_broad_tags_missing_vectors_and_markov_gaps():
    rows = [
        {
            "id": 1,
            "tags": ["Python", "Информационные технологии"],
            "difficulty": "normal",
            "embedding": [0.1],
            "cluster_id": 0,
            "tag_meta": {
                "unknown_raw_tags": ["OddTag"],
                "difficulty_meta": {
                    "source": "model",
                    "model_version": "selective-v1",
                    "strategy": "selective_easy_normal",
                },
            },
        },
        {
            "id": 2,
            "tags": ["Pandas"],
            "difficulty": None,
            "embedding": None,
            "cluster_id": None,
            "tag_meta": {"unknown_raw_tags": []},
        },
        {
            "id": 3,
            "tags": ["Python"],
            "difficulty": None,
            "embedding": [0.2],
            "cluster_id": 1,
            "tag_meta": {"difficulty_meta": {"source": "manual_holdout"}},
        },
    ]
    markov_matrix = {"Python": {"Pandas": 0.7, "NoCourseTag": 0.3}}

    metrics = compute_audit_metrics(
        rows,
        markov_matrix=markov_matrix,
        selective_difficulty_report={
            "status": "active",
            "model_version": "selective-v1",
            "allowed_levels": ["normal"],
            "thresholds": {"easy": 0.45, "normal": 0.50},
        },
    )

    assert metrics["course_count"] == 3
    assert metrics["broad_tag_assignments"] == 1
    assert metrics["missing_embeddings"] == 1
    assert metrics["missing_clusters"] == 1
    assert metrics["unknown_raw_tag_assignments"] == 1
    assert metrics["markov_next_tags_missing_in_db"] == 1
    assert metrics["missing_difficulty"] == 2
    assert metrics["difficulty_levels"] == {"normal": 1, "<missing>": 2}
    assert metrics["difficulty_sources"] == {"model": 1, "<missing>": 1, "manual_holdout": 1}
    assert metrics["trusted_training_difficulty_levels"] == {}
    assert metrics["difficulty_model_versions"] == {"selective-v1": 1}
    assert metrics["selective_difficulty_rows"] == 1
    assert metrics["selective_difficulty_gate_status"] == "active"
    assert metrics["selective_difficulty_allowed_levels"] == ["normal"]
    assert metrics["selective_difficulty_thresholds"] == {"easy": 0.45, "normal": 0.50}
