import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client
try:
    from data_pipeline.parcer.embedder import embed_courses
    from data_pipeline.pipeline import build_embedding_text, _source_hash
except ImportError:  # pragma: no cover
    from parcer.embedder import embed_courses
    from pipeline import build_embedding_text, _source_hash
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)





def run_embedding_backfill():
    print("Запускаем массовую векторизацию курсов")
    response = supabase.table("courses") \
        .select("id, title, summary, difficulty, tags, normalized_tags, tag_meta") \
        .is_("embedding", "null") \
        .execute()

    courses = response.data
    if not courses:
        print("Все курсы уже векторизованы")
        return

    print(f"Найдено курсов без векторов: {len(courses)}")

    updated_count = 0
    for course in courses:
        try:
            payload = {
                **course,
                "normalized_tags": course.get("normalized_tags") or course.get("tags") or [],
            }
            vector = embed_courses(build_embedding_text(payload), model_type="doc")
            meta = course.get("tag_meta") or {}
            meta["embedding_source_hash"] = _source_hash(payload)
            supabase.table("courses").update({"embedding": vector, "tag_meta": meta}).eq("id", course["id"]).execute()

            print(f"Векторизован курс [{course['id']}]: {course['title'][:30]}...")
            updated_count += 1

        except Exception as e:
            print(f"Ошибка на курсе {course['id']}: {e}")
        time.sleep(0.5)

    print(f"Готово! Добавлено векторов: {updated_count}.")


if __name__ == "__main__":
    run_embedding_backfill()
