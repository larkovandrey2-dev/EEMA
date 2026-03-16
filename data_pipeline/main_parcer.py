from parcer.fetch_stepik import fetch_top_stepik_courses
from db_client import insert_courses


def run_pipeline():
    print("Starting data pipeline")
    courses = fetch_top_stepik_courses(pages_to_fetch=1)
    if courses:
        insert_courses(courses)
    print("Finished data pipeline")
if __name__ == "__main__":
    run_pipeline()