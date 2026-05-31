import csv
import json

from ML.scripts import difficulty_prediction
from ML.scripts.difficulty_prediction import (
    DifficultyPrediction,
    SelectiveDifficultyPredictor,
    build_difficulty_feature_text,
    export_manual_holdout_template,
    load_manual_holdout,
    load_active_predictor,
    load_active_selective_predictor,
    train_selective_difficulty_model,
    train_difficulty_model,
)


def _course(course_id: int, level: str, token: str) -> dict:
    return {
        "id": course_id,
        "stepik_id": course_id,
        "title": f"{token} course",
        "summary": f"{token} practice {token}",
        "difficulty": level,
        "normalized_tags": [token],
        "tag_meta": {"difficulty_meta": {"source": "stepik"}},
    }


def _manual_course(course_id: int, level: str, token: str) -> dict:
    return {
        "id": course_id,
        "title": f"{token} course",
        "summary": f"{token} practice {token}",
        "normalized_tags": [token],
        "tag_meta": {"workload": ""},
        "manual_difficulty": level,
    }


class DeterministicSelectiveModel:
    classes_ = ["easy", "hard", "normal"]

    def fit(self, features, labels):
        return self

    def predict_proba(self, features):
        probabilities = []
        for text in features:
            if "starter" in text:
                probabilities.append([0.96, 0.02, 0.02])
            elif "applied" in text:
                probabilities.append([0.02, 0.02, 0.96])
            elif "uncertain" in text:
                probabilities.append([0.30, 0.25, 0.45])
            else:
                probabilities.append([0.02, 0.96, 0.02])
        return probabilities


def test_feature_text_uses_learning_content_without_leaking_target_or_commercial_fields():
    text = build_difficulty_feature_text(
        {
            "title": "Python workshop",
            "summary": "Learn pandas from examples",
            "normalized_tags": ["Python", "Pandas"],
            "tag_meta": {"workload": "10 hours"},
            "difficulty": "hard",
            "embedding": [0.12, 0.34],
            "price": 19990,
            "is_paid": True,
            "learners_count": 12345,
            "rating": 4.9,
        }
    )

    assert "Python workshop" in text
    assert "Pandas" in text
    assert "10 hours" in text
    assert "hard" not in text
    assert "19990" not in text
    assert "12345" not in text
    assert "0.12" not in text


def test_failed_training_does_not_replace_an_existing_active_model(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    active_meta = artifact_dir / "active_model.json"
    active_meta.write_text(json.dumps({"status": "active", "model_version": "previous"}))
    active_model = artifact_dir / "active_model.joblib"
    active_model.write_bytes(b"previous")

    report = train_difficulty_model(
        [_course(1, "easy", "basics")],
        [],
        artifact_dir=artifact_dir,
        min_source_per_class=2,
        min_holdout_per_class=1,
        cv_splits=2,
    )

    assert report["status"] == "rejected"
    assert "insufficient_source_labels" in report["reasons"]
    assert json.loads(active_meta.read_text())["model_version"] == "previous"
    assert active_model.read_bytes() == b"previous"


def test_successful_training_activates_model_and_failed_retrain_preserves_it(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    training = []
    holdout = []
    tokens = {"easy": "starter", "normal": "applied", "hard": "expert"}
    course_id = 0
    for level, token in tokens.items():
        for _ in range(4):
            course_id += 1
            training.append(_course(course_id, level, token))
        holdout.append({**_course(course_id + 100, level, token), "manual_difficulty": level})

    accepted = train_difficulty_model(
        training,
        holdout,
        artifact_dir=artifact_dir,
        min_source_per_class=2,
        min_holdout_per_class=1,
        cv_splits=2,
        source_macro_f1_min=0.0,
        source_recall_min=0.0,
        holdout_macro_f1_min=0.0,
        holdout_recall_min=0.0,
    )

    assert accepted["status"] == "active"
    predictor = load_active_predictor(artifact_dir=artifact_dir)
    prediction = predictor.predict(
        {"title": "expert workshop", "summary": "expert practice", "normalized_tags": ["expert"]}
    )
    assert isinstance(prediction, DifficultyPrediction)
    assert prediction.level in {"easy", "normal", "hard"}
    active_version = accepted["model_version"]

    rejected = train_difficulty_model(
        [_course(999, "easy", "starter")],
        [],
        artifact_dir=artifact_dir,
        min_source_per_class=2,
        min_holdout_per_class=1,
        cv_splits=2,
    )

    assert rejected["status"] == "rejected"
    assert json.loads((artifact_dir / "active_model.json").read_text())["model_version"] == active_version


def test_fifty_trusted_examples_per_class_are_enough_to_run_quality_validation(tmp_path):
    training = []
    holdout = []
    tokens = {"easy": "starter", "normal": "applied", "hard": "expert"}
    course_id = 0
    for level, token in tokens.items():
        for _ in range(50):
            course_id += 1
            training.append(_course(course_id, level, token))
        for _ in range(10):
            course_id += 1
            holdout.append({**_course(course_id, level, token), "manual_difficulty": level})

    report = train_difficulty_model(
        training,
        holdout,
        artifact_dir=tmp_path / "artifacts",
        source_macro_f1_min=0.0,
        source_recall_min=0.0,
        holdout_macro_f1_min=0.0,
        holdout_recall_min=0.0,
    )

    assert report["status"] == "active"
    assert "insufficient_source_labels" not in report["reasons"]


def test_manual_holdout_export_and_load_include_only_labelled_missing_courses(tmp_path):
    output_path = tmp_path / "holdout.csv"
    count = export_manual_holdout_template(
        [
            {"id": 1, "difficulty": "easy", "title": "Known"},
            {"id": 2, "stepik_id": 20, "difficulty": None, "title": "Unknown", "normalized_tags": ["Python"]},
        ],
        output_path=output_path,
        size=10,
    )

    assert count == 1
    with output_path.open(newline="", encoding="utf-8") as input_file:
        exported = list(csv.DictReader(input_file))
    exported[0]["manual_difficulty"] = "hard"
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=exported[0].keys())
        writer.writeheader()
        writer.writerows(exported)

    rows = load_manual_holdout(output_path)

    assert rows[0]["id"] == 2
    assert rows[0]["manual_difficulty"] == "hard"

    repeated = export_manual_holdout_template(
        [{"id": 3, "difficulty": None, "title": "New unknown"}],
        output_path=output_path,
        size=1,
    )
    assert repeated == 1
    assert load_manual_holdout(output_path)[0]["id"] == 2

    expanded = export_manual_holdout_template(
        [
            {"id": 2, "difficulty": None, "title": "Already exported"},
            {"id": 3, "stepik_id": 30, "difficulty": None, "title": "New unknown"},
        ],
        output_path=output_path,
        size=2,
    )
    assert expanded == 2
    with output_path.open(newline="", encoding="utf-8") as input_file:
        exported = list(csv.DictReader(input_file))
    assert [int(row["id"]) for row in exported] == [2, 3]
    assert exported[0]["manual_difficulty"] == "hard"
    assert exported[1]["manual_difficulty"] == ""


def test_selective_predictor_only_emits_allowed_confident_easy_or_normal_levels():
    predictor = SelectiveDifficultyPredictor(
        DeterministicSelectiveModel(),
        {
            "model_version": "selective-v1",
            "strategy": "selective_easy_normal",
            "allowed_levels": ["normal"],
            "thresholds": {"easy": 0.45, "normal": 0.50},
        },
    )

    accepted = predictor.predict({"title": "applied", "summary": "", "normalized_tags": []})

    assert accepted == DifficultyPrediction(
        level="normal",
        confidence=0.96,
        model_version="selective-v1",
        strategy="selective_easy_normal",
    )
    assert predictor.predict({"title": "starter", "summary": "", "normalized_tags": []}) is None
    assert predictor.predict({"title": "expert", "summary": "", "normalized_tags": []}) is None
    assert predictor.predict({"title": "uncertain", "summary": "", "normalized_tags": []}) is None


def test_selective_training_rejects_overlap_without_replacing_active_artifact(tmp_path, monkeypatch):
    artifact_dir = tmp_path / "selective"
    artifact_dir.mkdir()
    (artifact_dir / "active_model.json").write_text(json.dumps({"model_version": "previous"}))
    (artifact_dir / "active_model.joblib").write_bytes(b"previous")
    monkeypatch.setattr(difficulty_prediction, "_new_model", lambda: DeterministicSelectiveModel())
    training = [
        _manual_course(1, "easy", "starter"),
        _manual_course(2, "normal", "applied"),
        _manual_course(3, "hard", "expert"),
    ]
    holdout = [
        _manual_course(1, "easy", "starter"),
        _manual_course(4, "normal", "applied"),
        _manual_course(5, "hard", "expert"),
    ]

    report = train_selective_difficulty_model(training, holdout, artifact_dir=artifact_dir)

    assert report["status"] == "rejected"
    assert "overlapping_training_holdout_ids" in report["reasons"]
    assert json.loads((artifact_dir / "active_model.json").read_text())["model_version"] == "previous"
    assert (artifact_dir / "active_model.joblib").read_bytes() == b"previous"


def test_selective_training_activates_each_safe_output_class_independently(tmp_path, monkeypatch):
    monkeypatch.setattr(difficulty_prediction, "_new_model", lambda: DeterministicSelectiveModel())
    training = [
        _manual_course(1, "easy", "starter"),
        _manual_course(2, "normal", "applied"),
        _manual_course(3, "hard", "expert"),
    ]
    holdout = [
        _manual_course(10, "hard", "starter"),
        _manual_course(11, "normal", "applied"),
        _manual_course(12, "hard", "expert"),
        _manual_course(13, "easy", "expert"),
    ]

    report = train_selective_difficulty_model(
        training,
        holdout,
        artifact_dir=tmp_path / "selective",
        min_accepted_per_level=1,
    )

    assert report["status"] == "active"
    assert report["allowed_levels"] == ["normal"]
    assert report["selective_validation"]["easy"]["hard_mislabeled_count"] == 1
    assert report["selective_validation"]["normal"]["passed"] is True
    predictor = load_active_selective_predictor(artifact_dir=tmp_path / "selective")
    assert predictor.predict({"title": "applied", "summary": "", "normalized_tags": []}).level == "normal"
    assert predictor.predict({"title": "starter", "summary": "", "normalized_tags": []}) is None
