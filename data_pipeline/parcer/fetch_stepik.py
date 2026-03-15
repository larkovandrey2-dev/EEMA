import requests
import json
import time


def fetch_top_stepik_courses(pages_to_fetch=5):
    all_courses = []
    base_url = "https://stepik.org/api/courses"

    for page in range(1, pages_to_fetch + 1):
        params = {
            "is_public": "true",
            "is_popular": "true",
            "language": "ru",
            "page": page
        }

        response = requests.get(base_url, params=params)

        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code}")
            break

        data = response.json()
        courses = data.get("courses", [])

        for course in courses:
            clean_course = {
                "course_id": course["id"],
                "title": course["title"],
                "summary": course["summary"],
                "learners_count": course["learners_count"],
                "difficulty": course.get("difficulty", "unknown"),
                "rating": course.get("average_score", 0),
                "url": f"https://stepik.org/course/{course['id']}",
                "workload": course["workload"],
                "is_paid": course["is_paid"],
                "price": course["price"],

            }
            course_clean_tags = []
            tags = course.get("tags", [])
            for tag in tags:
                tag_url = f"https://stepik.org:443/api/tags/{tag}"
                tag_response = requests.get(tag_url)
                if tag_response.status_code != 200:
                    continue
                course_clean_tags.append(tag_response.json()['tags'][0]['title'])
            clean_course["tags"] = course_clean_tags
            all_courses.append(clean_course)
            print("Done fetching")

        time.sleep(0.05)


        if not data["meta"]["has_next"]:
            print("Достигнут конец списка!")
            break

    return all_courses


