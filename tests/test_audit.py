from data_pipeline.audit import compute_audit_metrics


def test_audit_reports_broad_tags_missing_vectors_and_markov_gaps():
    rows = [
        {
            "id": 1,
            "tags": ["Python", "Информационные технологии"],
            "embedding": [0.1],
            "cluster_id": 0,
            "tag_meta": {"unknown_raw_tags": ["OddTag"]},
        },
        {
            "id": 2,
            "tags": ["Pandas"],
            "embedding": None,
            "cluster_id": None,
            "tag_meta": {"unknown_raw_tags": []},
        },
    ]
    markov_matrix = {"Python": {"Pandas": 0.7, "NoCourseTag": 0.3}}

    metrics = compute_audit_metrics(rows, markov_matrix=markov_matrix)

    assert metrics["course_count"] == 2
    assert metrics["broad_tag_assignments"] == 1
    assert metrics["missing_embeddings"] == 1
    assert metrics["missing_clusters"] == 1
    assert metrics["unknown_raw_tag_assignments"] == 1
    assert metrics["markov_next_tags_missing_in_db"] == 1
