from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from data_pipeline.tag_normalizer import CANONICAL_TAGS, normalize_tags
except ImportError:  # pragma: no cover
    from tag_normalizer import CANONICAL_TAGS, normalize_tags


def build_mapping(raw_tags: list[str]) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    for raw_tag in raw_tags:
        result = normalize_tags([raw_tag])
        mapping[raw_tag] = result.normalized_tags[0] if result.normalized_tags else None
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic tag mapping JSON.")
    parser.add_argument("input", help="JSON file with a list of raw tags.")
    parser.add_argument("--output", default="tags_mapping.json")
    args = parser.parse_args()

    raw_tags = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(raw_tags, list):
        raise ValueError("Input JSON must be a list of raw tag strings")

    mapping = build_mapping([tag for tag in raw_tags if isinstance(tag, str)])
    Path(args.output).write_text(
        json.dumps(mapping, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    print(f"Saved {len(mapping)} mappings to {args.output}")
    print(f"Canonical taxonomy size: {len(CANONICAL_TAGS)}")


if __name__ == "__main__":
    main()
