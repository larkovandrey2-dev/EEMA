from datetime import datetime, timezone
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv
load_dotenv()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY"),
)

def insert_courses(courses: dict):
    success_count = 0
    for course in courses:
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            supabase.table('courses').upsert(
                {
                    "stepik_id": course["course_id"],
                    "title": course["title"],
                    "summary": course["summary"],
                    "difficulty": course["difficulty"],
                    "learners_count": course["learners_count"],
                    "rating": course["rating"],
                    "url": course["url"],
                    "tags": course["tags"],
                    "updated_at": current_time,
                    "is_paid": course["is_paid"],
                    "price": course["price"],
                }, on_conflict='stepik_id'
            ).execute()
            success_count += 1
        except Exception as e:
            print(e)
            print(course)
    print(f"Loaded {success_count} courses")


