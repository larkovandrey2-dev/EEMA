from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

try:
    from data_pipeline.pipeline import SupabaseCourseRepository, create_supabase_client
    from data_pipeline.tag_normalizer import BROAD_STOP_TAGS
except ImportError:  # pragma: no cover
    from pipeline import SupabaseCourseRepository, create_supabase_client
    from tag_normalizer import BROAD_STOP_TAGS


def compute_audit_metrics(
    rows: list[dict],
    *,
    markov_matrix: Mapping[str, Mapping[str, float]] | None = None,
) -> dict:
    db_tags = {
        tag
        for row in rows
        for tag in (row.get("tags") or [])
        if isinstance(tag, str)
    }
    broad_assignments = sum(
        1
        for row in rows
        for tag in (row.get("tags") or [])
        if tag in BROAD_STOP_TAGS
    )
    unknown_raw_tag_assignments = sum(
        len((row.get("tag_meta") or {}).get("unknown_raw_tags") or [])
        for row in rows
    )
    markov_next_tags = {
        tag
        for transitions in (markov_matrix or {}).values()
        for tag in transitions
    }
    missing_next_tags = sorted(markov_next_tags - db_tags)

    return {
        "course_count": len(rows),
        "unique_public_tags": len(db_tags),
        "broad_tag_assignments": broad_assignments,
        "missing_embeddings": sum(1 for row in rows if not row.get("embedding")),
        "missing_clusters": sum(1 for row in rows if row.get("cluster_id") is None),
        "unknown_raw_tag_assignments": unknown_raw_tag_assignments,
        "markov_next_tags_missing_in_db": len(missing_next_tags),
        "missing_markov_next_tags": missing_next_tags,
    }


def load_markov_matrix(path: str | Path) -> dict:
    matrix_path = Path(path)
    if not matrix_path.exists():
        return {}
    return json.loads(matrix_path.read_text(encoding="utf-8"))


def print_audit_report(metrics: dict) -> None:
    print("Data pipeline audit")
    print(f"- Courses: {metrics['course_count']}")
    print(f"- Unique public tags: {metrics['unique_public_tags']}")
    print(f"- Broad tag assignments in courses.tags: {metrics['broad_tag_assignments']}")
    print(f"- Missing embeddings: {metrics['missing_embeddings']}")
    print(f"- Missing clusters: {metrics['missing_clusters']}")
    print(f"- Unknown raw tag assignments: {metrics['unknown_raw_tag_assignments']}")
    print(f"- Markov next tags missing in DB: {metrics['markov_next_tags_missing_in_db']}")
    if metrics["missing_markov_next_tags"]:
        print("- Missing Markov tags sample:")
        for tag in metrics["missing_markov_next_tags"][:25]:
            print(f"  - {tag}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit recommendation data quality.")
    parser.add_argument(
        "--markov",
        default="ML/scripts/markov_matrix.json",
        help="Path to Markov matrix JSON.",
    )
    args = parser.parse_args()

    repository = SupabaseCourseRepository(create_supabase_client())
    rows = repository.iter_courses_for_audit()
    metrics = compute_audit_metrics(rows, markov_matrix=load_markov_matrix(args.markov))
    print_audit_report(metrics)


if __name__ == "__main__":
    main()
