import os
from supabase import create_client, Client
from dotenv import load_dotenv
try:
    from data_pipeline.tag_normalizer import normalize_tags
except ImportError:  # pragma: no cover
    from tag_normalizer import normalize_tags

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def apply_mapping_to_db():
    print("Начинаем очистку базы по детерминированной таксономии")
    response = supabase.table("courses").select("id, tags, raw_tags, tag_meta").execute()
    courses = response.data

    updated_count = 0
    for course in courses:
        source_tags = course.get("raw_tags") or course.get("tags")
        if not source_tags:
            continue

        normalized = normalize_tags(source_tags)
        tag_meta = course.get("tag_meta") or {}
        tag_meta.update(normalized.to_meta())
        if sorted(course.get("tags") or []) != sorted(normalized.normalized_tags):
            supabase.table("courses").update({
                "raw_tags": normalized.raw_tags,
                "normalized_tags": normalized.normalized_tags,
                "tags": normalized.normalized_tags,
                "domain": normalized.domain,
                "tag_meta": tag_meta,
            }).eq("id", course["id"]).execute()
            updated_count += 1

    print(f"Успешно нормализованы теги у {updated_count} курсов.")


if __name__ == "__main__":
    apply_mapping_to_db()
