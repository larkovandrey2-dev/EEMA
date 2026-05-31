from datetime import datetime, timezone
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
            record = {
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
                "embedding": course["embedding"],
            }
            for optional_field in ("raw_tags", "normalized_tags", "domain", "tag_meta"):
                if course.get(optional_field) is not None:
                    record[optional_field] = course[optional_field]

            supabase.table('courses').upsert(record, on_conflict='stepik_id').execute()
            success_count += 1
        except Exception as e:
            print(e)
            print(course)
    print(f"Loaded {success_count} courses")


def get_courses(pages_to_fetch:int = 5, course_on_page:int = 20):
    try:
        limit = pages_to_fetch * course_on_page
        courses = supabase.table('courses').select('stepik_id,title,summary,url,difficulty,learners_count,rating,tags,is_paid,price').limit(limit).execute().data
        clean_courses = []
        for page in range(pages_to_fetch):
            for course_num in range(course_on_page):
                list_course = course_on_page*page+course_num
                clean_courses.append({"course_num": list_course+1, "page": page+1, "course": courses[list_course]})
        return clean_courses
    except Exception as e:
        pass

def get_updating_date():
    try:
        date = supabase.table("courses").select("updated_at").order("updated_at",desc=True).limit(1).execute().data
        return datetime.fromisoformat(date[0]["updated_at"])
    except Exception as e:
        print(e)
