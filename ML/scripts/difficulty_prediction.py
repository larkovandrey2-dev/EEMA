from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "ML" / "artifacts" / "difficulty"
DEFAULT_HOLDOUT_PATH = PROJECT_ROOT / "ML" / "data" / "difficulty_manual_holdout.csv"
DEFAULT_SELECTIVE_ARTIFACT_DIR = DEFAULT_ARTIFACT_DIR / "selective"
DEFAULT_SELECTIVE_TRAINING_PATH = PROJECT_ROOT / "ML" / "data" / "difficulty_manual_holdout_labeled.csv"
DEFAULT_SELECTIVE_HOLDOUT_PATH = PROJECT_ROOT / "ML" / "data" / "difficulty_selective_activation_holdout.csv"
ACTIVE_MODEL_FILENAME = "active_model.joblib"
ACTIVE_METADATA_FILENAME = "active_model.json"
LATEST_REPORT_FILENAME = "latest_training_report.json"

VALID_DIFFICULTIES = ("easy", "normal", "hard")
TRUSTED_SOURCE_VALUES = {"stepik", "stepik_legacy"}
MIN_SOURCE_PER_CLASS = 50
MIN_HOLDOUT_PER_CLASS = 10
SOURCE_MACRO_F1_MIN = 0.60
SOURCE_RECALL_MIN = 0.50
HOLDOUT_MACRO_F1_MIN = 0.55
HOLDOUT_RECALL_MIN = 0.40
SELECTIVE_STRATEGY = "selective_easy_normal"
SELECTIVE_OUTPUT_LEVELS = ("easy", "normal")
SELECTIVE_THRESHOLDS = {"easy": 0.45, "normal": 0.50}
SELECTIVE_MIN_ACCEPTED_PER_LEVEL = 5
SELECTIVE_PRECISION_MIN = 0.90


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_difficulty(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if normalized in VALID_DIFFICULTIES else None


def build_difficulty_feature_text(course: dict) -> str:
    """Build difficulty-neutral model input; do not add ranking or target fields."""
    tags = course.get("normalized_tags") or course.get("tags") or []
    workload = (course.get("tag_meta") or {}).get("workload") or course.get("workload") or ""
    return "\n".join(
        [
            f"Title: {course.get('title') or ''}",
            f"Description: {course.get('summary') or ''}",
            f"Workload: {workload}",
            f"Tags: {', '.join(tags)}",
        ]
    )


@dataclass(frozen=True)
class DifficultyPrediction:
    level: str
    confidence: float
    model_version: str
    strategy: str | None = None


class ActiveDifficultyPredictor:
    def __init__(self, model: Pipeline, metadata: dict) -> None:
        self.model = model
        self.metadata = metadata
        self.model_version = metadata["model_version"]

    def predict(self, course: dict) -> DifficultyPrediction:
        text = build_difficulty_feature_text(course)
        level = str(self.model.predict([text])[0])
        probabilities = self.model.predict_proba([text])[0]
        confidence = float(max(probabilities))
        return DifficultyPrediction(
            level=level,
            confidence=round(confidence, 6),
            model_version=self.model_version,
            strategy=self.metadata.get("strategy"),
        )


class SelectiveDifficultyPredictor:
    def __init__(self, model: Pipeline, metadata: dict) -> None:
        self.model = model
        self.metadata = metadata
        self.model_version = metadata["model_version"]
        self.allowed_levels = set(metadata.get("allowed_levels") or [])
        self.thresholds = {
            level: float(value)
            for level, value in (metadata.get("thresholds") or SELECTIVE_THRESHOLDS).items()
        }

    def predict(self, course: dict) -> DifficultyPrediction | None:
        text = build_difficulty_feature_text(course)
        level, confidence = _predict_level_and_confidence(self.model, text)
        if level not in self.allowed_levels:
            return None
        if confidence < self.thresholds.get(level, 1.0):
            return None
        return DifficultyPrediction(
            level=level,
            confidence=round(confidence, 6),
            model_version=self.model_version,
            strategy=self.metadata.get("strategy", SELECTIVE_STRATEGY),
        )


def _new_model() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=40000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )


def _predict_level_and_confidence(model: Pipeline, text: str) -> tuple[str, float]:
    probabilities = model.predict_proba([text])[0]
    top_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    return str(model.classes_[top_index]), float(probabilities[top_index])


def _difficulty_source(row: dict) -> str:
    return ((row.get("tag_meta") or {}).get("difficulty_meta") or {}).get("source") or "stepik_legacy"


def _training_rows(rows: Iterable[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if normalize_difficulty(row.get("difficulty"))
        and _difficulty_source(row) in TRUSTED_SOURCE_VALUES
    ]


def _holdout_rows(rows: Iterable[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if normalize_difficulty(row.get("manual_difficulty") or row.get("difficulty"))
    ]


def _labels(rows: Iterable[dict], key: str = "difficulty") -> list[str]:
    return [normalize_difficulty(row.get(key)) or "" for row in rows]


def _reviewed_labels(rows: Iterable[dict]) -> list[str]:
    return [
        normalize_difficulty(row.get("manual_difficulty") or row.get("difficulty")) or ""
        for row in rows
    ]


def _metrics(y_true: list[str], y_pred: list[str]) -> dict:
    per_class_recall = recall_score(
        y_true,
        y_pred,
        labels=list(VALID_DIFFICULTIES),
        average=None,
        zero_division=0,
    )
    return {
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 6),
        "recall": {
            level: round(float(recall), 6)
            for level, recall in zip(VALID_DIFFICULTIES, per_class_recall)
        },
    }


def _minimum_recall(metrics: dict, classes: Iterable[str]) -> float:
    return min(metrics["recall"][level] for level in classes)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def train_difficulty_model(
    source_rows: list[dict],
    manual_holdout_rows: list[dict],
    *,
    artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR,
    min_source_per_class: int = MIN_SOURCE_PER_CLASS,
    min_holdout_per_class: int = MIN_HOLDOUT_PER_CLASS,
    cv_splits: int = 5,
    source_macro_f1_min: float = SOURCE_MACRO_F1_MIN,
    source_recall_min: float = SOURCE_RECALL_MIN,
    holdout_macro_f1_min: float = HOLDOUT_MACRO_F1_MIN,
    holdout_recall_min: float = HOLDOUT_RECALL_MIN,
) -> dict:
    artifact_dir = Path(artifact_dir)
    trusted_rows = _training_rows(source_rows)
    holdout_rows = _holdout_rows(manual_holdout_rows)
    source_counts = Counter(_labels(trusted_rows))
    holdout_labels = [
        normalize_difficulty(row.get("manual_difficulty") or row.get("difficulty")) or ""
        for row in holdout_rows
    ]
    holdout_counts = Counter(holdout_labels)
    version = f"difficulty-tfidf-logreg-v1-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    report = {
        "status": "rejected",
        "model_version": version,
        "trained_at": _now_iso(),
        "feature_schema": ["title", "summary", "normalized_tags", "workload"],
        "excluded_features": [
            "difficulty",
            "embedding",
            "price",
            "is_paid",
            "learners_count",
            "rating",
        ],
        "source_label_counts": {level: source_counts.get(level, 0) for level in VALID_DIFFICULTIES},
        "holdout_label_counts": {level: holdout_counts.get(level, 0) for level in VALID_DIFFICULTIES},
        "holdout_ids": [row.get("id") for row in holdout_rows if row.get("id") is not None],
        "reasons": [],
    }

    if any(source_counts.get(level, 0) < min_source_per_class for level in VALID_DIFFICULTIES):
        report["reasons"].append("insufficient_source_labels")
    if any(holdout_counts.get(level, 0) < min_holdout_per_class for level in VALID_DIFFICULTIES):
        report["reasons"].append("insufficient_manual_holdout")
    if report["reasons"]:
        _write_json(artifact_dir / LATEST_REPORT_FILENAME, report)
        return report

    x_source = [build_difficulty_feature_text(row) for row in trusted_rows]
    y_source = _labels(trusted_rows)
    model = _new_model()
    cross_validation = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    source_predictions = cross_val_predict(model, x_source, y_source, cv=cross_validation)
    source_metrics = _metrics(y_source, list(source_predictions))
    report["source_validation"] = source_metrics
    if source_metrics["macro_f1"] < source_macro_f1_min:
        report["reasons"].append("source_macro_f1_below_gate")
    if _minimum_recall(source_metrics, VALID_DIFFICULTIES) < source_recall_min:
        report["reasons"].append("source_recall_below_gate")

    model.fit(x_source, y_source)
    x_holdout = [build_difficulty_feature_text(row) for row in holdout_rows]
    holdout_predictions = model.predict(x_holdout)
    holdout_metrics = _metrics(holdout_labels, list(holdout_predictions))
    report["holdout_validation"] = holdout_metrics
    if holdout_metrics["macro_f1"] < holdout_macro_f1_min:
        report["reasons"].append("holdout_macro_f1_below_gate")
    if _minimum_recall(holdout_metrics, VALID_DIFFICULTIES) < holdout_recall_min:
        report["reasons"].append("holdout_recall_below_gate")

    _write_json(artifact_dir / LATEST_REPORT_FILENAME, report)
    if report["reasons"]:
        return report

    report["status"] = "active"
    model_path = artifact_dir / ACTIVE_MODEL_FILENAME
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    _write_json(artifact_dir / ACTIVE_METADATA_FILENAME, report)
    _write_json(artifact_dir / LATEST_REPORT_FILENAME, report)
    return report


def load_active_predictor(
    *,
    artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR,
) -> ActiveDifficultyPredictor | None:
    artifact_dir = Path(artifact_dir)
    metadata_path = artifact_dir / ACTIVE_METADATA_FILENAME
    model_path = artifact_dir / ACTIVE_MODEL_FILENAME
    if not metadata_path.exists() or not model_path.exists():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "active":
        return None
    return ActiveDifficultyPredictor(joblib.load(model_path), metadata)


def train_selective_difficulty_model(
    development_rows: list[dict],
    activation_holdout_rows: list[dict],
    *,
    artifact_dir: str | Path = DEFAULT_SELECTIVE_ARTIFACT_DIR,
    thresholds: dict[str, float] | None = None,
    min_accepted_per_level: int = SELECTIVE_MIN_ACCEPTED_PER_LEVEL,
    precision_min: float = SELECTIVE_PRECISION_MIN,
) -> dict:
    artifact_dir = Path(artifact_dir)
    thresholds = {**SELECTIVE_THRESHOLDS, **(thresholds or {})}
    training_rows = _holdout_rows(development_rows)
    holdout_rows = _holdout_rows(activation_holdout_rows)
    training_labels = _reviewed_labels(training_rows)
    holdout_labels = _reviewed_labels(holdout_rows)
    training_counts = Counter(training_labels)
    holdout_counts = Counter(holdout_labels)
    training_ids = {row["id"] for row in training_rows if row.get("id") is not None}
    holdout_ids = {row["id"] for row in holdout_rows if row.get("id") is not None}
    version = f"difficulty-selective-tfidf-logreg-v1-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    report = {
        "status": "rejected",
        "strategy": SELECTIVE_STRATEGY,
        "model_version": version,
        "trained_at": _now_iso(),
        "feature_schema": ["title", "summary", "normalized_tags", "workload"],
        "excluded_features": [
            "difficulty",
            "embedding",
            "price",
            "is_paid",
            "learners_count",
            "rating",
        ],
        "thresholds": thresholds,
        "allowed_levels": [],
        "training_label_counts": {level: training_counts.get(level, 0) for level in VALID_DIFFICULTIES},
        "holdout_label_counts": {level: holdout_counts.get(level, 0) for level in VALID_DIFFICULTIES},
        "training_ids": sorted(training_ids),
        "holdout_ids": sorted(holdout_ids),
        "reasons": [],
    }

    if training_ids & holdout_ids:
        report["reasons"].append("overlapping_training_holdout_ids")
    if any(training_counts.get(level, 0) == 0 for level in VALID_DIFFICULTIES):
        report["reasons"].append("insufficient_selective_training_labels")
    if any(holdout_counts.get(level, 0) == 0 for level in VALID_DIFFICULTIES):
        report["reasons"].append("insufficient_selective_holdout_labels")
    if report["reasons"]:
        _write_json(artifact_dir / LATEST_REPORT_FILENAME, report)
        return report

    model = _new_model()
    model.fit([build_difficulty_feature_text(row) for row in training_rows], training_labels)
    holdout_predictions = [
        _predict_level_and_confidence(model, build_difficulty_feature_text(row))
        for row in holdout_rows
    ]
    selective_validation: dict[str, dict] = {}
    allowed_levels: list[str] = []
    for level in SELECTIVE_OUTPUT_LEVELS:
        accepted_indexes = [
            index
            for index, (predicted_level, confidence) in enumerate(holdout_predictions)
            if predicted_level == level and confidence >= thresholds[level]
        ]
        accepted_count = len(accepted_indexes)
        correct_count = sum(holdout_labels[index] == level for index in accepted_indexes)
        hard_mislabeled_count = sum(holdout_labels[index] == "hard" for index in accepted_indexes)
        precision = correct_count / accepted_count if accepted_count else 0.0
        passed = (
            accepted_count >= min_accepted_per_level
            and precision >= precision_min
            and hard_mislabeled_count == 0
        )
        selective_validation[level] = {
            "threshold": thresholds[level],
            "accepted_count": accepted_count,
            "coverage": round(accepted_count / len(holdout_rows), 6),
            "correct_count": correct_count,
            "precision": round(precision, 6),
            "hard_mislabeled_count": hard_mislabeled_count,
            "passed": passed,
        }
        if passed:
            allowed_levels.append(level)
        else:
            report["reasons"].append(f"{level}_selective_gate_failed")

    report["selective_validation"] = selective_validation
    report["allowed_levels"] = allowed_levels
    _write_json(artifact_dir / LATEST_REPORT_FILENAME, report)
    if not allowed_levels:
        return report

    report["status"] = "active"
    model_path = artifact_dir / ACTIVE_MODEL_FILENAME
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    _write_json(artifact_dir / ACTIVE_METADATA_FILENAME, report)
    _write_json(artifact_dir / LATEST_REPORT_FILENAME, report)
    return report


def load_active_selective_predictor(
    *,
    artifact_dir: str | Path = DEFAULT_SELECTIVE_ARTIFACT_DIR,
) -> SelectiveDifficultyPredictor | None:
    artifact_dir = Path(artifact_dir)
    metadata_path = artifact_dir / ACTIVE_METADATA_FILENAME
    model_path = artifact_dir / ACTIVE_MODEL_FILENAME
    if not metadata_path.exists() or not model_path.exists():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "active" or metadata.get("strategy") != SELECTIVE_STRATEGY:
        return None
    if not metadata.get("allowed_levels"):
        return None
    return SelectiveDifficultyPredictor(joblib.load(model_path), metadata)


def export_manual_holdout_template(
    rows: list[dict],
    *,
    output_path: str | Path = DEFAULT_HOLDOUT_PATH,
    size: int = 90,
) -> int:
    output_path = Path(output_path)
    fields = ["id", "stepik_id", "title", "summary", "normalized_tags", "workload", "manual_difficulty"]
    existing_records: list[dict] = []
    if output_path.exists():
        with output_path.open(newline="", encoding="utf-8") as input_file:
            existing_records = list(csv.DictReader(input_file))
    existing_ids = {
        int(row["id"])
        for row in existing_records
        if row.get("id")
    }
    missing_rows = [
        row
        for row in rows
        if normalize_difficulty(row.get("difficulty")) is None
        and int(row.get("id") or 0) not in existing_ids
        and (((row.get("tag_meta") or {}).get("difficulty_meta") or {}).get("source")) != "manual_holdout"
    ]
    new_limit = max(size - len(existing_records), 0)
    selected = sorted(missing_rows, key=lambda row: int(row.get("id") or 0))[:new_limit]
    records = list(existing_records)
    records.extend(
        {
            "id": row.get("id"),
            "stepik_id": row.get("stepik_id"),
            "title": row.get("title") or "",
            "summary": row.get("summary") or "",
            "normalized_tags": json.dumps(
                row.get("normalized_tags") or row.get("tags") or [],
                ensure_ascii=False,
            ),
            "workload": (row.get("tag_meta") or {}).get("workload") or "",
            "manual_difficulty": "",
        }
        for row in selected
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    return len(records)


def manual_holdout_course_ids(path: str | Path) -> set[int]:
    path = Path(path)
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as input_file:
        return {
            int(row["id"])
            for row in csv.DictReader(input_file)
            if row.get("id")
        }


def load_manual_holdout(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            label = normalize_difficulty(row.get("manual_difficulty"))
            if not label:
                continue
            try:
                tags = json.loads(row.get("normalized_tags") or "[]")
            except json.JSONDecodeError:
                tags = []
            rows.append(
                {
                    "id": int(row["id"]) if row.get("id") else None,
                    "stepik_id": int(row["stepik_id"]) if row.get("stepik_id") else None,
                    "title": row.get("title") or "",
                    "summary": row.get("summary") or "",
                    "normalized_tags": tags,
                    "tag_meta": {"workload": row.get("workload") or ""},
                    "manual_difficulty": label,
                }
            )
    return rows
