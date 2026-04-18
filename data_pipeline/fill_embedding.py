import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client
from parcer.embedder import embed_courses
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)





def run_embedding_backfill():
    print("Запускаем массовую векторизацию курсов")
    response = supabase.table("courses") \
        .select("id, title, summary, difficulty, tags") \
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
            tags_str = ", ".join(course.get('tags') or [])
            text_to_embed = f"Название: {course['title']}\nОписание: {course.get('summary', '')}\nСложность: {course.get('difficulty', 'unknown')}\nТеги: {tags_str}"
            vector = embed_courses(text_to_embed)
            supabase.table("courses").update({"embedding": vector}).eq("id", course["id"]).execute()

            print(f"Векторизован курс [{course['id']}]: {course['title'][:30]}...")
            updated_count += 1

        except Exception as e:
            print(f"Ошибка на курсе {course['id']}: {e}")
        time.sleep(0.5)

    print(f"Готово! Добавлено векторов: {updated_count}.")


if __name__ == "__main__":
    run_embedding_backfill()