from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable


TAXONOMY_VERSION = "2026-05-24-it-mvp-v1"


BROAD_STOP_TAGS = {
    "Информационные технологии",
    "Учебные и академические дисциплины",
    "Языки программирования",
    "Разработка программного обеспечения",
    "Software Development",
    "Software and Development Tools",
    "Programming",
    "Digital Literacy",
    "Цифровая грамотность",
    "Informatics",
    "Информатика",
    "Технологии и инновации",
    "AI Skills",
    "Навыки работы с ИИ",
    "Online Courses",
    "Online Course",
    "Online Learning",
    "E-learning",
    "Education",
}


IT_BROAD_HINTS = BROAD_STOP_TAGS | {
    "Фреймворки и библиотеки",
    "ПО и инструменты для разработки",
    "Программное обеспечение и инструменты",
    "Базы данных",
    "Веб-разработка",
    "Кибербезопасность",
}


BUSINESS_TAGS = {
    "Project Management",
    "Product Management",
    "Business Analysis",
    "Business Analytics",
    "Digital Marketing",
    "Marketing",
    "Finance",
    "Soft Skills",
}


TAG_META = {
    "Python": {"level": "skill", "domain": "it"},
    "JavaScript": {"level": "skill", "domain": "it"},
    "TypeScript": {"level": "skill", "domain": "it"},
    "Java": {"level": "skill", "domain": "it"},
    "C++": {"level": "skill", "domain": "it"},
    "C#": {"level": "skill", "domain": "it"},
    "Go": {"level": "skill", "domain": "it"},
    "SQL": {"level": "skill", "domain": "it"},
    "NoSQL": {"level": "area", "domain": "it"},
    "PostgreSQL": {"level": "tool", "domain": "it", "parent": "SQL"},
    "MySQL": {"level": "tool", "domain": "it", "parent": "SQL"},
    "MongoDB": {"level": "tool", "domain": "it", "parent": "NoSQL"},
    "Pandas": {"level": "tool", "domain": "it", "parent": "Python"},
    "NumPy": {"level": "tool", "domain": "it", "parent": "Python"},
    "SciPy": {"level": "tool", "domain": "it", "parent": "Python"},
    "Matplotlib": {"level": "tool", "domain": "it", "parent": "Python"},
    "React": {"level": "framework", "domain": "it", "parent": "JavaScript"},
    "Vue.js": {"level": "framework", "domain": "it", "parent": "JavaScript"},
    "Angular": {"level": "framework", "domain": "it", "parent": "JavaScript"},
    "Node.js": {"level": "framework", "domain": "it", "parent": "JavaScript"},
    "Django": {"level": "framework", "domain": "it", "parent": "Python"},
    "FastAPI": {"level": "framework", "domain": "it", "parent": "Python"},
    "Flask": {"level": "framework", "domain": "it", "parent": "Python"},
    "Spring": {"level": "framework", "domain": "it", "parent": "Java"},
    "Spring Boot": {"level": "framework", "domain": "it", "parent": "Java"},
    "Docker": {"level": "tool", "domain": "it"},
    "Kubernetes": {"level": "tool", "domain": "it"},
    "Linux": {"level": "skill", "domain": "it"},
    "Git": {"level": "tool", "domain": "it"},
    "REST API": {"level": "skill", "domain": "it"},
    "GraphQL": {"level": "skill", "domain": "it"},
    "FastAPI": {"level": "framework", "domain": "it", "parent": "Python"},
    "Data Science": {"level": "area", "domain": "it"},
    "Data Analysis": {"level": "area", "domain": "it"},
    "Data Analytics": {"level": "area", "domain": "it"},
    "Machine Learning": {"level": "area", "domain": "it"},
    "Deep Learning": {"level": "area", "domain": "it"},
    "Artificial Intelligence": {"level": "area", "domain": "it"},
    "Natural Language Processing": {"level": "area", "domain": "it"},
    "Computer Vision": {"level": "area", "domain": "it"},
    "Web Development": {"level": "area", "domain": "it"},
    "Frontend": {"level": "area", "domain": "it"},
    "Backend": {"level": "area", "domain": "it"},
    "DevOps": {"level": "area", "domain": "it"},
    "Cybersecurity": {"level": "area", "domain": "it"},
    "Information Security": {"level": "area", "domain": "it"},
    "Databases": {"level": "area", "domain": "it"},
    "Algorithms": {"level": "area", "domain": "it"},
    "Data Structures": {"level": "area", "domain": "it"},
    "Project Management": {"level": "area", "domain": "business_adjacent"},
    "Product Management": {"level": "area", "domain": "business_adjacent"},
    "Business Analysis": {"level": "area", "domain": "business_adjacent"},
    "Business Analytics": {"level": "area", "domain": "business_adjacent"},
    "Digital Marketing": {"level": "area", "domain": "business_adjacent"},
    "Marketing": {"level": "area", "domain": "business_adjacent"},
    "Finance": {"level": "area", "domain": "business_adjacent"},
    "Soft Skills": {"level": "area", "domain": "business_adjacent"},
}


CANONICAL_TAGS = set(TAG_META)


ALIASES = {
    "пайтон": "Python",
    "питон": "Python",
    "python": "Python",
    "py": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "reactjs": "React",
    "react": "React",
    "react.js": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "django": "Django",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "flask": "Flask",
    "spring": "Spring",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "num py": "NumPy",
    "scipy": "SciPy",
    "matplotlib": "Matplotlib",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "sql": "SQL",
    "nosql": "NoSQL",
    "docker": "Docker",
    "docker compose": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "linux": "Linux",
    "git": "Git",
    "rest": "REST API",
    "restapi": "REST API",
    "rest api": "REST API",
    "graphql": "GraphQL",
    "data science": "Data Science",
    "наука о данных": "Data Science",
    "анализ данных": "Data Analysis",
    "обработка и анализ данных": "Data Analysis",
    "data analysis": "Data Analysis",
    "data analytics": "Data Analytics",
    "аналитика и исследование данных": "Data Analytics",
    "машинное обучение": "Machine Learning",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "глубинное обучение": "Deep Learning",
    "deep learning": "Deep Learning",
    "искусственный интеллект": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "ai": "Artificial Intelligence",
    "nlp": "Natural Language Processing",
    "обработка естественного языка": "Natural Language Processing",
    "computer vision": "Computer Vision",
    "компьютерное зрение": "Computer Vision",
    "web development": "Web Development",
    "webdevelopment": "Web Development",
    "web-development": "Web Development",
    "веб-разработка": "Web Development",
    "frontend": "Frontend",
    "фронтенд": "Frontend",
    "фронтенд-разработка": "Frontend",
    "backend": "Backend",
    "бекенд": "Backend",
    "бэкенд": "Backend",
    "бэкенд-разработка": "Backend",
    "api": "REST API",
    "апи": "REST API",
    "devops": "DevOps",
    "devops и системное администрирование": "DevOps",
    "cybersecurity": "Cybersecurity",
    "кибербезопасность": "Cybersecurity",
    "information security": "Information Security",
    "информационная безопасность и кибербезопасность": "Information Security",
    "databases": "Databases",
    "database": "Databases",
    "базы данных": "Databases",
    "algorithms": "Algorithms",
    "алгоритмы и структуры данных": "Algorithms",
    "data structures": "Data Structures",
    "project management": "Project Management",
    "проектный менеджмент": "Project Management",
    "product management": "Product Management",
    "business analysis": "Business Analysis",
    "бизнес-анализ": "Business Analysis",
    "business analytics": "Business Analytics",
    "digital marketing": "Digital Marketing",
    "marketing": "Marketing",
    "маркетинг": "Marketing",
    "finance": "Finance",
    "финансы": "Finance",
    "soft skills": "Soft Skills",
    "гибкие навыки": "Soft Skills",
}

for canonical in CANONICAL_TAGS:
    ALIASES.setdefault(canonical.casefold(), canonical)


@dataclass(frozen=True)
class NormalizedTags:
    raw_tags: list[str]
    normalized_tags: list[str]
    dropped_tags: list[str]
    unknown_raw_tags: list[str]
    domain: str

    def to_meta(self) -> dict:
        return {
            "taxonomy_version": TAXONOMY_VERSION,
            "dropped_tags": self.dropped_tags,
            "unknown_raw_tags": self.unknown_raw_tags,
            "tag_levels": {tag: TAG_META.get(tag, {}).get("level", "area") for tag in self.normalized_tags},
            "tag_parents": {
                tag: TAG_META[tag]["parent"]
                for tag in self.normalized_tags
                if "parent" in TAG_META.get(tag, {})
            },
            "domain": self.domain,
        }


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _alias_key(value: str) -> str:
    cleaned = _clean_text(value).casefold()
    compact = re.sub(r"[_./]+", " ", cleaned)
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact


def _compact_alias_key(value: str) -> str:
    return re.sub(r"[\s_./-]+", "", _alias_key(value))


def _canonical_from_alias(raw_tag: str) -> str | None:
    key = _alias_key(raw_tag)
    if key in ALIASES:
        return ALIASES[key]
    compact = _compact_alias_key(raw_tag)
    return ALIASES.get(compact)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def normalize_tags(
    raw_tags: list[str] | None,
    *,
    llm_mapping: dict[str, str | None] | None = None,
    allow_llm: bool = False,
    llm_mapper: Callable[[list[str]], dict[str, str | None]] | None = None,
) -> NormalizedTags:
    raw_tags = [_clean_text(tag) for tag in (raw_tags or []) if isinstance(tag, str) and tag.strip()]
    llm_mapping = dict(llm_mapping or {})

    normalized: list[str] = []
    dropped: list[str] = []
    unknown: list[str] = []
    has_it_signal = False
    has_business_signal = False

    for raw_tag in raw_tags:
        if raw_tag in IT_BROAD_HINTS:
            has_it_signal = True
        if raw_tag in BROAD_STOP_TAGS:
            _append_unique(dropped, raw_tag)
            continue

        canonical = _canonical_from_alias(raw_tag)
        if canonical:
            _append_unique(normalized, canonical)
            meta = TAG_META.get(canonical, {})
            has_it_signal = has_it_signal or meta.get("domain") == "it"
            has_business_signal = has_business_signal or meta.get("domain") == "business_adjacent"
            continue

        mapped = llm_mapping.get(raw_tag)
        if mapped in CANONICAL_TAGS:
            _append_unique(normalized, mapped)
            meta = TAG_META.get(mapped, {})
            has_it_signal = has_it_signal or meta.get("domain") == "it"
            has_business_signal = has_business_signal or meta.get("domain") == "business_adjacent"
            continue

        if allow_llm and llm_mapper:
            llm_mapping.update(llm_mapper([raw_tag]))
            mapped = llm_mapping.get(raw_tag)
            if mapped in CANONICAL_TAGS:
                _append_unique(normalized, mapped)
                meta = TAG_META.get(mapped, {})
                has_it_signal = has_it_signal or meta.get("domain") == "it"
                has_business_signal = has_business_signal or meta.get("domain") == "business_adjacent"
                continue

        _append_unique(unknown, raw_tag)

    if has_it_signal or any(TAG_META.get(tag, {}).get("domain") == "it" for tag in normalized):
        domain = "it"
    elif has_business_signal or any(tag in BUSINESS_TAGS for tag in normalized):
        domain = "business_adjacent"
    else:
        domain = "other"

    return NormalizedTags(
        raw_tags=raw_tags,
        normalized_tags=normalized,
        dropped_tags=dropped,
        unknown_raw_tags=unknown,
        domain=domain,
    )
