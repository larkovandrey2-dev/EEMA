import requests
try:
    from data_pipeline.parcer.embedder import embed_courses
    from data_pipeline.stepik_client import StepikClient
    from data_pipeline.pipeline import build_course_payload, build_embedding_text
except ImportError:  # pragma: no cover
    from parcer.embedder import embed_courses
    from stepik_client import StepikClient
    from pipeline import build_course_payload, build_embedding_text

def fetch_top_stepik_courses(pages_to_fetch=5):
    client = StepikClient(session=requests.Session())
    courses = client.fetch_popular_courses(pages_to_fetch=pages_to_fetch)
    tags_by_course_id = client.fetch_tags_for_courses(courses)
    payloads = []

    for course in courses:
        payload = build_course_payload(
            course,
            raw_tags=tags_by_course_id.get(int(course["id"]), []),
        )
        payload["course_id"] = payload["stepik_id"]
        payload["embedding"] = embed_courses(build_embedding_text(payload), model_type="doc")
        payloads.append(payload)

    return payloads
