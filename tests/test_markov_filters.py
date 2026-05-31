from ML.scripts.markov import filter_transition_matrix


def test_markov_filters_missing_and_broad_targets_then_renormalizes():
    matrix = {
        "Python": {
            "Pandas": 0.4,
            "React": 0.2,
            "Информационные технологии": 0.2,
            "NoCourseTag": 0.2,
        },
        "Информационные технологии": {"Python": 1.0},
    }

    filtered = filter_transition_matrix(
        matrix,
        available_tags={"Python", "Pandas", "React"},
        broad_tags={"Информационные технологии"},
    )

    assert set(filtered) == {"Python"}
    assert filtered["Python"] == {"Pandas": 0.666667, "React": 0.333333}
