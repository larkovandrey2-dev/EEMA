import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import requests

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

YC_API_KEY = os.getenv("YC_API_KEY")
YC_FOLDER_ID = os.getenv("YC_FOLDER_ID")


def ask_yagpt(system_prompt: str, user_text: str, temperature: float = 0.0) -> str:
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YC_API_KEY}",
        "x-folder-id": YC_FOLDER_ID,
    }
    model_uri = f"gpt://{YC_FOLDER_ID}/yandexgpt/latest"
    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": "1500"
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_text}
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Ошибка Yandex API ({response.status_code}): {response.text}")
    data = response.json()
    try:
        return data["result"]["alternatives"][0]["message"]["text"]
    except (KeyError, IndexError):
        raise Exception("YandexGPT вернул неожиданный формат ответа")


def run_enrichment():
    print("Начинаем обогащение базы умными тегами...")

    response = supabase.table("courses").select("id, title, summary, tags").order("learners_count", desc=True).limit(
        1000).execute()
    courses = response.data

    print(f"Найдено курсов для обработки: {len(courses)}")

    system_prompt = """
    Ты IT-эксперт. Твоя задача — выделить 3-5 ключевых технологий, языков или сфер ИЗ ОПИСАНИЯ курса.
    Пиши теги СТРОГО на АНГЛИЙСКОМ языке (например: Python, Data Science, Backend, Machine Learning).
    ВЕРНИ ТОЛЬКО СЛОВА ЧЕРЕЗ ЗАПЯТУЮ. Никакого текста до или после. Никаких точек в конце.
    """

    updated_count = 0

    for course in courses:
        if not course['title']:
            continue

        user_text = f"Название: {course['title']}\nОписание: {course.get('summary', '')}"

        try:
            raw_tags = ask_yagpt(system_prompt, user_text)

            new_tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]

            if new_tags:
                old_tags = course.get('tags') or []
                combined_tags = list(set(old_tags + new_tags))

                supabase.table("courses").update({"tags": combined_tags}).eq("id", course['id']).execute()

                print(f"✅ [{course['id']}] {course['title'][:30]}... -> {new_tags}")
                updated_count += 1

        except Exception as e:
            print(f"❌ Ошибка на курсе {course['id']}: {e}")

        time.sleep(1)

    print(f"Готово! Успешно добавлено тегов: {updated_count} курсов.")


if __name__ == "__main__":
    run_enrichment()