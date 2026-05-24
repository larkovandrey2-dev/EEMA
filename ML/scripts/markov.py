from __future__ import annotations

from collections.abc import Mapping

try:
    from data_pipeline.tag_normalizer import BROAD_STOP_TAGS
except ImportError:  # pragma: no cover
    BROAD_STOP_TAGS = set()


def filter_transition_matrix(
    matrix: Mapping[str, Mapping[str, float]],
    *,
    available_tags: set[str],
    broad_tags: set[str] | None = None,
) -> dict[str, dict[str, float]]:
    broad_tags = set(BROAD_STOP_TAGS if broad_tags is None else broad_tags)
    filtered_matrix: dict[str, dict[str, float]] = {}

    for source_tag, transitions in matrix.items():
        if source_tag in broad_tags or source_tag not in available_tags:
            continue

        filtered_transitions: dict[str, float] = {}
        for target_tag, score in transitions.items():
            if target_tag == source_tag:
                continue
            if target_tag in broad_tags or target_tag not in available_tags:
                continue
            if score <= 0:
                continue
            filtered_transitions[target_tag] = float(score)

        total = sum(filtered_transitions.values())
        if total <= 0:
            continue

        filtered_matrix[source_tag] = {
            tag: round(score / total, 6)
            for tag, score in filtered_transitions.items()
        }

    return filtered_matrix


def get_next_tags(
    matrix: Mapping[str, Mapping[str, float]],
    current_tags: list[str],
    *,
    available_tags: set[str],
    top_k: int = 2,
    broad_tags: set[str] | None = None,
) -> list[str]:
    filtered = filter_transition_matrix(matrix, available_tags=available_tags, broad_tags=broad_tags)
    scores: dict[str, float] = {}
    current = set(current_tags)
    for tag in current_tags:
        for next_tag, score in filtered.get(tag, {}).items():
            if next_tag not in current:
                scores[next_tag] = scores.get(next_tag, 0.0) + score
    return [
        tag
        for tag, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    ]
