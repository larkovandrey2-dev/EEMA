# EEMA Data Pipeline

Пайплайн наполняет Supabase курсами Stepik и готовит данные для RAG, кластеров и Markov.

## Перед первым запуском

Применить миграцию:

```bash
supabase db push
```

или выполнить SQL из:

```text
supabase-project/migrations/20260524_courses_pipeline_fields.sql
```

Она добавляет совместимые поля `raw_tags`, `normalized_tags`, `domain`, `tag_meta`.
Поле `courses.tags` остается публичным alias для фронта.

## Команды

```bash
python3 -m data_pipeline.pipeline ingest --pages 5
python3 -m data_pipeline.pipeline difficulty-export --output ML/data/difficulty_manual_holdout.csv --size 90
python3 -m data_pipeline.pipeline difficulty-train --holdout ML/data/difficulty_manual_holdout.csv
python3 -m data_pipeline.pipeline difficulty-selective-train --training ML/data/difficulty_manual_holdout_labeled.csv --holdout ML/data/difficulty_selective_activation_holdout.csv
python3 -m data_pipeline.pipeline difficulty
python3 -m data_pipeline.pipeline taxonomy-cache
python3 -m data_pipeline.pipeline cluster
python3 -m data_pipeline.pipeline markov
python3 -m data_pipeline.pipeline audit
python3 -m data_pipeline.pipeline all --pages 5
```

Для быстрого dry run без Yandex embeddings:

```bash
python3 -m data_pipeline.pipeline ingest --pages 1 --skip-embed
```

## Что происходит

- `ingest`: fetch Stepik courses, batch-fetch tags, normalize tags, upsert courses, refresh embeddings when source text changes.
- `difficulty-export`: экспортирует курсы без сложности в CSV для независимой ручной разметки и резервирует эти строки как `manual_holdout`, чтобы модель не заполнила их до проверки человеком.
- `difficulty-train`: переобучает `TF-IDF + LogisticRegression` на доверенных Stepik-метках и активирует модель только после source/holdout quality gate.
- `difficulty-selective-train`: обучает отдельную missing-source модель и активирует только безопасно подтвержденные выходы `easy`/`normal` на новом непересекающемся holdout.
- `difficulty`: применяет активную строгую модель, а при ее отсутствии активную selective-модель, к оставшимся `NULL difficulty` и перевекторизует только измененные курсы.
- `taxonomy-cache`: строит `data_pipeline/taxonomy_embeddings.json` для semantic query-understanding по каноничным тегам.
- `cluster`: пересчитывает `cluster_id` по embeddings.
- `markov`: строит `ML/scripts/markov_matrix.json` только по каноничным тегам, которые есть в базе.
- `audit`: печатает метрики качества: broad tags, missing embeddings/clusters, unknown raw tags, Markov gaps.

## Difficulty enrichment

Stepik-level has priority. For a course without source difficulty, `ingest` may use only a previously activated gated model; manual holdout rows and Stepik labels are never overwritten by model inference. `manual_holdout` is assigned at export time, while its `difficulty` may remain `NULL` until the CSV is labelled and imported by a training stage. The holdout is persistent: rerunning `difficulty-export` with the same `--size` preserves its labels, and rerunning it with a larger `--size` appends new rows without replacing the existing sample. Internal provenance lives in `tag_meta.difficulty_meta` with `source` values `stepik`, `stepik_legacy`, `manual_holdout`, or `model`; selective model rows additionally store `strategy=selective_easy_normal`.

The strict three-class model remains in `ML/artifacts/difficulty/active_model.joblib`. A separate selective artifact lives under `ML/artifacts/difficulty/selective/` and may output only gate-approved `easy` and/or `normal`; it always abstains on predicted `hard` and low-confidence rows. A strict active model takes precedence over selective inference. Both paths use only `title`, `summary`, canonical tags, and workload, never the RAG embedding because that embedding includes the difficulty label.

Training uses only trusted Stepik labels (`stepik` and `stepik_legacy`); `manual_holdout` labels appear in catalogue totals but are excluded from training and used only for independent validation. Validation begins once there are at least `50` trusted examples of each level; activation still requires all source and holdout metric gates.

Selective training uses `ML/data/difficulty_manual_holdout_labeled.csv` as development data for missing-source courses. It must be evaluated on a new disjoint `ML/data/difficulty_selective_activation_holdout.csv`. Each output class is activated independently only if the holdout has at least five accepted predictions, accepted precision is at least `0.90`, and no real `hard` row is accepted as that easier level. Fixed confidence thresholds are `easy >= 0.45` and `normal >= 0.50`.

Recommended refresh flow after ingesting a larger Stepik sample:

```bash
python3 -m data_pipeline.pipeline ingest --pages 250
python3 -m data_pipeline.pipeline audit
python3 -m data_pipeline.pipeline difficulty-export --output ML/data/difficulty_manual_holdout.csv --size 90
# Fill manual_difficulty with easy/normal/hard in the CSV.
# If there are fewer than 10 real examples of any level, append candidates:
# python3 -m data_pipeline.pipeline difficulty-export --output ML/data/difficulty_manual_holdout.csv --size 180
python3 -m data_pipeline.pipeline difficulty-train --holdout ML/data/difficulty_manual_holdout.csv
python3 -m data_pipeline.pipeline difficulty
python3 -m data_pipeline.pipeline cluster
python3 -m data_pipeline.pipeline audit
```

`--pages` always reads the first N Stepik result pages and upserts by `stepik_id`; it does not append N unseen pages after previous runs. Increase it beyond earlier coverage and use `audit` to confirm that `Courses` and trusted `hard` counts actually grew.

Threshold-based ordinal experiments are allowed only as future model candidates evaluated by the same three-class gate. Threshold tuning must not force `hard` predictions without holdout evidence.

Selective MVP flow after the development CSV has been prepared:

```bash
python3 -m data_pipeline.pipeline difficulty-export --output ML/data/difficulty_selective_activation_holdout.csv --size 180
# Fill manual_difficulty with easy/normal/hard in the new CSV.
python3 -m data_pipeline.pipeline difficulty-selective-train \
  --training ML/data/difficulty_manual_holdout_labeled.csv \
  --holdout ML/data/difficulty_selective_activation_holdout.csv
python3 -m data_pipeline.pipeline difficulty
python3 -m data_pipeline.pipeline cluster
python3 -m data_pipeline.pipeline audit
```

Do not use `difficulty_manual_holdout_labeled.csv` as the selective activation holdout: it has already been inspected during model selection.

Узкие технологии сохраняются как отдельные теги: `Pandas`, `React`, `Django`, `FastAPI`, `PostgreSQL` не заменяются родителями вроде `Python`, `JavaScript` или `SQL`.
