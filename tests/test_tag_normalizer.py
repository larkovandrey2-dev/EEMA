from data_pipeline.tag_normalizer import normalize_tags


def test_normalizer_keeps_specific_technologies_and_drops_broad_tags():
    result = normalize_tags(
        [
            "Информационные технологии",
            "Учебные и академические дисциплины",
            "Пайтон",
            "python",
            "Pandas",
            "React.JS",
            "Django",
            "Fast API",
            "PostgreSQL",
            "TotallyUnknownThing",
        ]
    )

    assert result.normalized_tags == [
        "Python",
        "Pandas",
        "React",
        "Django",
        "FastAPI",
        "PostgreSQL",
    ]
    assert "Информационные технологии" in result.dropped_tags
    assert "Учебные и академические дисциплины" in result.dropped_tags
    assert result.unknown_raw_tags == ["TotallyUnknownThing"]
    assert result.domain == "it"


def test_llm_mapping_is_allowed_only_when_target_is_canonical_tag():
    result = normalize_tags(
        ["Странный тег", "Еще один тег"],
        llm_mapping={
            "Странный тег": "Pandas",
            "Еще один тег": "Made Up Parent",
        },
    )

    assert "Pandas" in result.normalized_tags
    assert "Made Up Parent" not in result.normalized_tags
    assert result.unknown_raw_tags == ["Еще один тег"]
