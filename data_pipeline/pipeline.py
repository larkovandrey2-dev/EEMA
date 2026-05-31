from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable

from dotenv import load_dotenv
from supabase import Client, create_client

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from ML.scripts.difficulty_prediction import (
        DEFAULT_HOLDOUT_PATH,
        DEFAULT_SELECTIVE_TRAINING_PATH,
        DifficultyPrediction,
        export_manual_holdout_template,
        load_active_predictor,
        load_active_selective_predictor,
        load_manual_holdout,
        manual_holdout_course_ids,
        normalize_difficulty,
        train_difficulty_model,
        train_selective_difficulty_model,
    )
    from data_pipeline.parcer.embedder import embed_courses
    from data_pipeline.stepik_client import StepikClient
    from data_pipeline.tag_normalizer import ALIASES, CANONICAL_TAGS, TAG_META, TAXONOMY_VERSION, NormalizedTags, normalize_tags
except ImportError:  # pragma: no cover - keeps direct script execution working
    from ML.scripts.difficulty_prediction import (
        DEFAULT_HOLDOUT_PATH,
        DEFAULT_SELECTIVE_TRAINING_PATH,
        DifficultyPrediction,
        export_manual_holdout_template,
        load_active_predictor,
        load_active_selective_predictor,
        load_manual_holdout,
        manual_holdout_course_ids,
        normalize_difficulty,
        train_difficulty_model,
        train_selective_difficulty_model,
    )
    from parcer.embedder import embed_courses
    from stepik_client import StepikClient
    from tag_normalizer import ALIASES, CANONICAL_TAGS, TAG_META, TAXONOMY_VERSION, NormalizedTags, normalize_tags


NormalizeFn = Callable[[list[str]], NormalizedTags]
EmbedFn = Callable[[str], list[float]]
_AUTO_PREDICTOR = object()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model_difficulty_meta(prediction: DifficultyPrediction) -> dict:
    metadata = {
        "source": "model",
        "model_version": prediction.model_version,
        "confidence": prediction.confidence,
        "predicted_at": _now_iso(),
    }
    if prediction.strategy:
        metadata["strategy"] = prediction.strategy
    return metadata


def load_difficulty_predictor() -> Any | None:
    return load_active_predictor() or load_active_selective_predictor()


def build_embedding_text(payload: dict) -> str:
    tags = ", ".join(payload.get("normalized_tags") or payload.get("tags") or [])
    workload = payload.get("tag_meta", {}).get("workload") or ""
    return "\n".join(
        [
            f"Title: {payload.get('title') or ''}",
            f"Description: {payload.get('summary') or ''}",
            f"Difficulty: {payload.get('difficulty') or 'unknown'}",
            f"Workload: {workload}",
            f"Tags: {tags}",
        ]
    )


def _source_hash(payload: dict) -> str:
    return hashlib.sha256(build_embedding_text(payload).encode("utf-8")).hexdigest()


def _aliases_by_tag() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for alias, canonical in ALIASES.items():
        if canonical not in CANONICAL_TAGS:
            continue
        grouped.setdefault(canonical, [])
        if alias not in grouped[canonical]:
            grouped[canonical].append(alias)
    return grouped


def build_taxonomy_embedding_text(tag: str, aliases_by_tag: dict[str, list[str]] | None = None) -> str:
    aliases_by_tag = aliases_by_tag or _aliases_by_tag()
    meta = TAG_META.get(tag, {})
    aliases = ", ".join(sorted(set(aliases_by_tag.get(tag, []))))
    return "\n".join(
        [
            f"Tag: {tag}",
            f"Level: {meta.get('level') or 'unknown'}",
            f"Domain: {meta.get('domain') or 'unknown'}",
            f"Parent: {meta.get('parent') or ''}",
            f"Aliases: {aliases}",
        ]
    )


def build_taxonomy_embedding_cache(
    *,
    output_path: Path | str = ROOT_DIR / "data_pipeline" / "taxonomy_embeddings.json",
    embed_fn: EmbedFn | None = None,
    tags: list[str] | None = None,
    request_delay_seconds: float = 0.15,
    max_retries: int = 3,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    embed_fn = embed_fn or (lambda text: embed_courses(text, model_type="doc"))
    output_path = Path(output_path)
    aliases_by_tag = _aliases_by_tag()
    selected_tags = sorted(tags or CANONICAL_TAGS)
    items = []

    for tag in selected_tags:
        if tag not in CANONICAL_TAGS:
            continue
        text = build_taxonomy_embedding_text(tag, aliases_by_tag)
        embedding = None
        for attempt in range(max_retries + 1):
            try:
                embedding = embed_fn(text)
                break
            except RuntimeError as error:
                is_rate_limit = "429" in str(error) or "quota" in str(error).lower()
                if not is_rate_limit or attempt >= max_retries:
                    raise
                sleep_fn(float(2 ** attempt))
        items.append(
            {
                "tag": tag,
                "text": text,
                "embedding": embedding,
            }
        )
        if request_delay_seconds > 0:
            sleep_fn(request_delay_seconds)

    payload = {
        "taxonomy_version": TAXONOMY_VERSION,
        "model": "text-search-doc",
        "items": items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(items)


def build_course_payload(
    course: dict,
    *,
    raw_tags: list[str],
    normalize: NormalizeFn = normalize_tags,
    existing_row: dict | None = None,
    difficulty_predictor: Any | None = None,
) -> dict:
    normalized = normalize(raw_tags)
    tag_meta = normalized.to_meta()
    tag_meta["workload"] = course.get("workload") or ""

    payload = {
        "stepik_id": course["id"],
        "title": course.get("title") or "",
        "summary": course.get("summary") or "",
        "learners_count": course.get("learners_count") or 0,
        "rating": course.get("average_score", course.get("rating") or 0) or 0,
        "url": course.get("url") or f"https://stepik.org/course/{course['id']}",
        "raw_tags": normalized.raw_tags,
        "normalized_tags": normalized.normalized_tags,
        "tags": normalized.normalized_tags,
        "domain": normalized.domain,
        "tag_meta": tag_meta,
        "updated_at": _now_iso(),
        "is_paid": bool(course.get("is_paid", False)),
        "price": course.get("price"),
    }
    source_level = normalize_difficulty(course.get("difficulty"))
    existing_level = normalize_difficulty((existing_row or {}).get("difficulty"))
    existing_meta = ((existing_row or {}).get("tag_meta") or {}).get("difficulty_meta")
    existing_source = (existing_meta or {}).get("source")

    if source_level:
        payload["difficulty"] = source_level
        tag_meta["difficulty_meta"] = {"source": "stepik"}
    elif existing_level:
        payload["difficulty"] = existing_level
        tag_meta["difficulty_meta"] = existing_meta or {"source": "stepik_legacy"}
    elif existing_source == "manual_holdout":
        payload["difficulty"] = None
        tag_meta["difficulty_meta"] = existing_meta
    elif difficulty_predictor:
        prediction: DifficultyPrediction | None = difficulty_predictor.predict(payload)
        if prediction:
            payload["difficulty"] = prediction.level
            tag_meta["difficulty_meta"] = _model_difficulty_meta(prediction)
        else:
            payload["difficulty"] = None
    else:
        payload["difficulty"] = None
    payload["tag_meta"]["embedding_source_hash"] = _source_hash(payload)
    return payload


def needs_embedding(existing_row: dict | None, payload: dict) -> bool:
    if not existing_row or not existing_row.get("embedding"):
        return True
    old_meta = existing_row.get("tag_meta") or {}
    new_meta = payload.get("tag_meta") or {}
    return old_meta.get("embedding_source_hash") != new_meta.get("embedding_source_hash")


class SupabaseCourseRepository:
    def __init__(self, supabase: Client) -> None:
        self.supabase = supabase

    def get_existing_by_stepik_id(self, stepik_id: int) -> dict | None:
        response = (
            self.supabase.table("courses")
            .select("id, stepik_id, difficulty, embedding, tag_meta")
            .eq("stepik_id", stepik_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_course_by_id(self, course_id: int) -> dict | None:
        response = (
            self.supabase.table("courses")
            .select("id, stepik_id, title, summary, difficulty, tags, normalized_tags, tag_meta, embedding")
            .eq("id", course_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def upsert_course(self, payload: dict) -> None:
        self.supabase.table("courses").upsert(payload, on_conflict="stepik_id").execute()

    def update_course(self, course_id: int, fields: dict) -> None:
        self.supabase.table("courses").update(fields).eq("id", course_id).execute()

    def iter_courses_for_audit(self) -> list[dict]:
        rows: list[dict] = []
        page_size = 1000
        page = 0
        while True:
            response = (
                self.supabase.table("courses")
                .select("id, difficulty, tags, raw_tags, normalized_tags, domain, tag_meta, embedding, cluster_id")
                .range(page * page_size, page * page_size + page_size - 1)
                .execute()
            )
            batch = response.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                return rows
            page += 1

    def iter_courses_for_difficulty(self, *, only_missing: bool = False) -> list[dict]:
        rows: list[dict] = []
        page_size = 1000
        page = 0
        while True:
            query = self.supabase.table("courses").select(
                "id, stepik_id, title, summary, difficulty, tags, normalized_tags, tag_meta"
            )
            if only_missing:
                query = query.is_("difficulty", "null")
            response = query.range(page * page_size, page * page_size + page_size - 1).execute()
            batch = response.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                return rows
            page += 1


def backfill_missing_difficulty(
    rows: list[dict],
    *,
    predictor: Any | None,
    update_course: Callable[[int, dict], None],
    embed_fn: EmbedFn,
) -> int:
    if predictor is None:
        return 0
    updated_count = 0
    for row in rows:
        if normalize_difficulty(row.get("difficulty")):
            continue
        source = (((row.get("tag_meta") or {}).get("difficulty_meta") or {}).get("source"))
        if source == "manual_holdout":
            continue
        prediction: DifficultyPrediction | None = predictor.predict(row)
        if prediction is None:
            continue
        tag_meta = dict(row.get("tag_meta") or {})
        tag_meta["difficulty_meta"] = _model_difficulty_meta(prediction)
        payload = {**row, "difficulty": prediction.level, "tag_meta": tag_meta}
        tag_meta["embedding_source_hash"] = _source_hash(payload)
        update_course(
            int(row["id"]),
            {
                "difficulty": prediction.level,
                "tag_meta": tag_meta,
                "embedding": embed_fn(build_embedding_text(payload)),
                "updated_at": _now_iso(),
            },
        )
        updated_count += 1
    return updated_count


def reserve_manual_holdout_rows(
    rows: list[dict],
    *,
    size: int,
    update_course: Callable[[int, dict], None],
    reserved_ids: set[int] | None = None,
) -> int:
    candidates = sorted(
        [row for row in rows if not normalize_difficulty(row.get("difficulty"))],
        key=lambda row: int(row.get("id") or 0),
    )
    if reserved_ids is not None:
        candidates = [row for row in candidates if int(row.get("id") or 0) in reserved_ids]
    selected = candidates[:size]
    for row in selected:
        tag_meta = dict(row.get("tag_meta") or {})
        tag_meta["difficulty_meta"] = {"source": "manual_holdout"}
        update_course(int(row["id"]), {"tag_meta": tag_meta})
    return len(selected)


def apply_manual_holdout_labels(
    rows: list[dict],
    *,
    repository: SupabaseCourseRepository,
    embed_fn: EmbedFn,
) -> int:
    updated_count = 0
    for labelled_row in rows:
        course_id = labelled_row.get("id")
        level = normalize_difficulty(labelled_row.get("manual_difficulty"))
        if course_id is None or not level:
            continue
        existing = repository.get_course_by_id(int(course_id))
        if not existing:
            continue
        source = (((existing.get("tag_meta") or {}).get("difficulty_meta") or {}).get("source"))
        if normalize_difficulty(existing.get("difficulty")) and source not in {"model", "manual_holdout"}:
            continue
        if normalize_difficulty(existing.get("difficulty")) == level and source == "manual_holdout":
            continue
        tag_meta = dict(existing.get("tag_meta") or {})
        tag_meta["difficulty_meta"] = {"source": "manual_holdout"}
        payload = {**existing, "difficulty": level, "tag_meta": tag_meta}
        tag_meta["embedding_source_hash"] = _source_hash(payload)
        repository.update_course(
            int(course_id),
            {
                "difficulty": level,
                "tag_meta": tag_meta,
                "embedding": embed_fn(build_embedding_text(payload)),
                "updated_at": _now_iso(),
            },
        )
        updated_count += 1
    return updated_count


def fetch_normalize_upsert(
    *,
    stepik: StepikClient,
    repository: SupabaseCourseRepository,
    pages_to_fetch: int = 5,
    embed: bool = True,
    difficulty_predictor: Any = _AUTO_PREDICTOR,
) -> int:
    if difficulty_predictor is _AUTO_PREDICTOR:
        difficulty_predictor = load_difficulty_predictor()
    courses = stepik.fetch_popular_courses(pages_to_fetch=pages_to_fetch)
    tags_by_course_id = stepik.fetch_tags_for_courses(courses)
    updated_count = 0

    for course in courses:
        existing = repository.get_existing_by_stepik_id(int(course["id"]))
        payload = build_course_payload(
            course,
            raw_tags=tags_by_course_id.get(int(course["id"]), []),
            existing_row=existing,
            difficulty_predictor=difficulty_predictor,
        )
        if embed and needs_embedding(existing, payload):
            payload["embedding"] = embed_courses(build_embedding_text(payload), model_type="doc")
        repository.upsert_course(payload)
        updated_count += 1

    return updated_count


def create_supabase_client() -> Client:
    load_dotenv()
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def run_data_pipeline(*, pages_to_fetch: int = 5, embed: bool = True) -> int:
    repository = SupabaseCourseRepository(create_supabase_client())
    stepik = StepikClient()
    return fetch_normalize_upsert(
        stepik=stepik,
        repository=repository,
        pages_to_fetch=pages_to_fetch,
        embed=embed,
    )


def run_cluster_stage() -> None:
    from ML.scripts.run_clusterising import run_ml_pipeline

    run_ml_pipeline()


def run_markov_stage() -> None:
    from ML.scripts.build_markov import build_markov_matrix

    build_markov_matrix()


def run_audit_stage() -> None:
    from data_pipeline.audit import compute_audit_metrics, load_difficulty_report, load_markov_matrix, print_audit_report

    repository = SupabaseCourseRepository(create_supabase_client())
    rows = repository.iter_courses_for_audit()
    metrics = compute_audit_metrics(
        rows,
        markov_matrix=load_markov_matrix("ML/scripts/markov_matrix.json"),
        difficulty_report=load_difficulty_report("ML/artifacts/difficulty/latest_training_report.json"),
        selective_difficulty_report=load_difficulty_report(
            "ML/artifacts/difficulty/selective/latest_training_report.json"
        ),
    )
    print_audit_report(metrics)


def run_taxonomy_cache_stage() -> int:
    return build_taxonomy_embedding_cache()


def run_difficulty_export_stage(*, output_path: str | Path, size: int) -> int:
    repository = SupabaseCourseRepository(create_supabase_client())
    rows = repository.iter_courses_for_difficulty(only_missing=True)
    count = export_manual_holdout_template(rows, output_path=output_path, size=size)
    reserve_manual_holdout_rows(
        rows,
        size=size,
        reserved_ids=manual_holdout_course_ids(output_path),
        update_course=repository.update_course,
    )
    return count


def run_difficulty_train_stage(*, holdout_path: str | Path) -> dict:
    repository = SupabaseCourseRepository(create_supabase_client())
    source_rows = repository.iter_courses_for_difficulty()
    holdout_rows = load_manual_holdout(holdout_path)
    report = train_difficulty_model(source_rows, holdout_rows)
    manual_updates = apply_manual_holdout_labels(
        holdout_rows,
        repository=repository,
        embed_fn=lambda text: embed_courses(text, model_type="doc"),
    )
    report["manual_holdout_updates"] = manual_updates
    return report


def run_difficulty_selective_train_stage(*, training_path: str | Path, holdout_path: str | Path) -> dict:
    repository = SupabaseCourseRepository(create_supabase_client())
    training_rows = load_manual_holdout(training_path)
    holdout_rows = load_manual_holdout(holdout_path)
    report = train_selective_difficulty_model(training_rows, holdout_rows)
    manual_updates = apply_manual_holdout_labels(
        holdout_rows,
        repository=repository,
        embed_fn=lambda text: embed_courses(text, model_type="doc"),
    )
    report["manual_holdout_updates"] = manual_updates
    return report


def run_difficulty_stage() -> int:
    predictor = load_difficulty_predictor()
    if predictor is None:
        print("Difficulty enrichment skipped: no active strict or selective gated model")
        return 0
    repository = SupabaseCourseRepository(create_supabase_client())
    rows = repository.iter_courses_for_difficulty(only_missing=True)
    return backfill_missing_difficulty(
        rows,
        predictor=predictor,
        update_course=repository.update_course,
        embed_fn=lambda text: embed_courses(text, model_type="doc"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch, normalize and upsert Stepik courses.")
    parser.add_argument(
        "stage",
        nargs="?",
        default="ingest",
        choices=[
            "ingest",
            "difficulty-export",
            "difficulty-train",
            "difficulty-selective-train",
            "difficulty",
            "cluster",
            "markov",
            "audit",
            "taxonomy-cache",
            "all",
        ],
        help="Pipeline stage to run.",
    )
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_HOLDOUT_PATH))
    parser.add_argument("--size", type=int, default=90)
    parser.add_argument("--holdout", default=str(DEFAULT_HOLDOUT_PATH))
    parser.add_argument("--training", default=str(DEFAULT_SELECTIVE_TRAINING_PATH))
    args = parser.parse_args()

    if args.stage in {"ingest", "all"}:
        count = run_data_pipeline(pages_to_fetch=args.pages, embed=not args.skip_embed)
        print(f"Upserted {count} courses")
    if args.stage == "difficulty-export":
        count = run_difficulty_export_stage(output_path=args.output, size=args.size)
        print(f"Exported {count} courses for manual difficulty labelling to {args.output}")
    if args.stage == "difficulty-train":
        report = run_difficulty_train_stage(holdout_path=args.holdout)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.stage == "difficulty-selective-train":
        report = run_difficulty_selective_train_stage(
            training_path=args.training,
            holdout_path=args.holdout,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.stage in {"difficulty", "all"}:
        count = run_difficulty_stage()
        print(f"Difficulty enriched {count} courses")
    if args.stage in {"cluster", "all"}:
        run_cluster_stage()
    if args.stage in {"markov", "all"}:
        run_markov_stage()
    if args.stage in {"audit", "all"}:
        run_audit_stage()
    if args.stage == "taxonomy-cache":
        count = run_taxonomy_cache_stage()
        print(f"Cached {count} taxonomy tag embeddings")


if __name__ == "__main__":
    main()
