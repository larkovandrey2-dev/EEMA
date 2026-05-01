import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def apply_mapping_to_db():
    print("Начинаем очистку базы по маппингу")
    with open("tags_mapping.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    response = supabase.table("courses").select("id, tags").execute()
    courses = response.data

    updated_count = 0
    for course in courses:
        old_tags = course.get("tags")
        if not old_tags:
            continue

        new_tags = []
        for tag in old_tags:
            mapped_tag = mapping.get(tag, tag)

            if mapped_tag is not None:
                new_tags.append(mapped_tag)
        new_tags = list(set(new_tags))

        if sorted(old_tags) != sorted(new_tags):
            supabase.table("courses").update({"tags": new_tags}).eq("id", course["id"]).execute()
            updated_count += 1

    print(f"Успешно обновлены теги у {updated_count} курсов.")


if __name__ == "__main__":
    apply_mapping_to_db()