from __future__ import annotations

from typing import Any

import requests


class StepikClient:
    def __init__(
        self,
        *,
        base_url: str = "https://stepik.org",
        session: Any | None = None,
        timeout: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_popular_courses(self, *, pages_to_fetch: int = 5, language: str = "ru") -> list[dict]:
        courses: list[dict] = []
        for page in range(1, pages_to_fetch + 1):
            response = self.session.get(
                f"{self.base_url}/api/courses",
                params={
                    "is_public": "true",
                    "is_popular": "true",
                    "language": language,
                    "page": page,
                },
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Stepik courses API error {response.status_code}: {response.text}")
            payload = response.json()
            courses.extend(payload.get("courses", []))
            if not payload.get("meta", {}).get("has_next"):
                break
        return courses

    def fetch_tags_by_ids(self, tag_ids: list[int], *, batch_size: int = 100) -> dict[int, str]:
        unique_ids = list(dict.fromkeys(tag_ids))
        tag_titles: dict[int, str] = {}

        for offset in range(0, len(unique_ids), batch_size):
            batch = unique_ids[offset : offset + batch_size]
            if not batch:
                continue
            response = self.session.get(
                f"{self.base_url}/api/tags",
                params={"ids[]": batch},
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Stepik tags API error {response.status_code}: {response.text}")
            for tag in response.json().get("tags", []):
                tag_titles[int(tag["id"])] = tag["title"]

        return tag_titles

    def fetch_tags_for_courses(self, courses: list[dict]) -> dict[int, list[str]]:
        all_tag_ids: list[int] = []
        for course in courses:
            all_tag_ids.extend(course.get("tags") or [])

        titles_by_id = self.fetch_tags_by_ids(all_tag_ids)
        result: dict[int, list[str]] = {}
        for course in courses:
            result[int(course["id"])] = [
                titles_by_id[tag_id]
                for tag_id in (course.get("tags") or [])
                if tag_id in titles_by_id
            ]
        return result
