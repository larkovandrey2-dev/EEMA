from __future__ import annotations

import argparse
from collections import Counter
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
    difficulty_report: Mapping[str, object] | None = None,
    selective_difficulty_report: Mapping[str, object] | None = None,
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
    difficulty_levels = Counter()
    difficulty_sources = Counter()
    trusted_training_difficulty_levels = Counter()
    difficulty_model_versions = Counter()
    selective_difficulty_rows = 0
    for row in rows:
        level = row.get("difficulty") or "<missing>"
        difficulty_levels[level] += 1
        difficulty_meta = (row.get("tag_meta") or {}).get("difficulty_meta") or {}
        source = difficulty_meta.get("source")
        if not source:
            source = "<missing>" if level == "<missing>" else "stepik_legacy"
        difficulty_sources[source] += 1
        if source in {"stepik", "stepik_legacy"} and level != "<missing>":
            trusted_training_difficulty_levels[level] += 1
        if source == "model" and difficulty_meta.get("model_version"):
            difficulty_model_versions[difficulty_meta["model_version"]] += 1
        if source == "model" and difficulty_meta.get("strategy") == "selective_easy_normal":
            selective_difficulty_rows += 1

    return {
        "course_count": len(rows),
        "unique_public_tags": len(db_tags),
        "broad_tag_assignments": broad_assignments,
        "missing_embeddings": sum(1 for row in rows if not row.get("embedding")),
        "missing_clusters": sum(1 for row in rows if row.get("cluster_id") is None),
        "unknown_raw_tag_assignments": unknown_raw_tag_assignments,
        "markov_next_tags_missing_in_db": len(missing_next_tags),
        "missing_markov_next_tags": missing_next_tags,
        "missing_difficulty": difficulty_levels["<missing>"],
        "difficulty_levels": dict(difficulty_levels),
        "difficulty_sources": dict(difficulty_sources),
        "trusted_training_difficulty_levels": dict(trusted_training_difficulty_levels),
        "difficulty_model_versions": dict(difficulty_model_versions),
        "difficulty_gate_status": (difficulty_report or {}).get("status", "not_trained"),
        "difficulty_gate_model_version": (difficulty_report or {}).get("model_version"),
        "selective_difficulty_rows": selective_difficulty_rows,
        "selective_difficulty_gate_status": (selective_difficulty_report or {}).get("status", "not_trained"),
        "selective_difficulty_gate_model_version": (selective_difficulty_report or {}).get("model_version"),
        "selective_difficulty_allowed_levels": list(
            (selective_difficulty_report or {}).get("allowed_levels") or []
        ),
        "selective_difficulty_thresholds": dict(
            (selective_difficulty_report or {}).get("thresholds") or {}
        ),
    }


def load_markov_matrix(path: str | Path) -> dict:
    matrix_path = Path(path)
    if not matrix_path.exists():
        return {}
    return json.loads(matrix_path.read_text(encoding="utf-8"))


def load_difficulty_report(path: str | Path) -> dict:
    report_path = Path(path)
    if not report_path.exists():
        return {}
    return json.loads(report_path.read_text(encoding="utf-8"))


def print_audit_report(metrics: dict) -> None:
    print("Data pipeline audit")
    print(f"- Courses: {metrics['course_count']}")
    print(f"- Unique public tags: {metrics['unique_public_tags']}")
    print(f"- Broad tag assignments in courses.tags: {metrics['broad_tag_assignments']}")
    print(f"- Missing embeddings: {metrics['missing_embeddings']}")
    print(f"- Missing clusters: {metrics['missing_clusters']}")
    print(f"- Unknown raw tag assignments: {metrics['unknown_raw_tag_assignments']}")
    print(f"- Missing difficulty: {metrics['missing_difficulty']}")
    print(f"- Difficulty levels: {metrics['difficulty_levels']}")
    print(f"- Difficulty sources: {metrics['difficulty_sources']}")
    print(f"- Training-eligible difficulty levels: {metrics['trusted_training_difficulty_levels']}")
    print(f"- Difficulty model versions: {metrics['difficulty_model_versions']}")
    print(
        f"- Difficulty gate: {metrics['difficulty_gate_status']}"
        f" ({metrics['difficulty_gate_model_version'] or 'no active version'})"
    )
    print(f"- Selective difficulty rows: {metrics['selective_difficulty_rows']}")
    print(
        f"- Selective difficulty gate: {metrics['selective_difficulty_gate_status']}"
        f" ({metrics['selective_difficulty_gate_model_version'] or 'no active version'})"
    )
    print(f"- Selective allowed levels: {metrics['selective_difficulty_allowed_levels']}")
    print(f"- Selective thresholds: {metrics['selective_difficulty_thresholds']}")
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
    parser.add_argument(
        "--difficulty-report",
        default="ML/artifacts/difficulty/latest_training_report.json",
        help="Path to the latest difficulty model gate report.",
    )
    parser.add_argument(
        "--selective-difficulty-report",
        default="ML/artifacts/difficulty/selective/latest_training_report.json",
        help="Path to the latest selective difficulty model gate report.",
    )
    args = parser.parse_args()

    repository = SupabaseCourseRepository(create_supabase_client())
    rows = repository.iter_courses_for_audit()
    metrics = compute_audit_metrics(
        rows,
        markov_matrix=load_markov_matrix(args.markov),
        difficulty_report=load_difficulty_report(args.difficulty_report),
        selective_difficulty_report=load_difficulty_report(args.selective_difficulty_report),
    )
    print_audit_report(metrics)


if __name__ == "__main__":
    main()
