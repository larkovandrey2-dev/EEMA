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
- `taxonomy-cache`: строит `data_pipeline/taxonomy_embeddings.json` для semantic query-understanding по каноничным тегам.
- `cluster`: пересчитывает `cluster_id` по embeddings.
- `markov`: строит `ML/scripts/markov_matrix.json` только по каноничным тегам, которые есть в базе.
- `audit`: печатает метрики качества: broad tags, missing embeddings/clusters, unknown raw tags, Markov gaps.

Узкие технологии сохраняются как отдельные теги: `Pandas`, `React`, `Django`, `FastAPI`, `PostgreSQL` не заменяются родителями вроде `Python`, `JavaScript` или `SQL`.
