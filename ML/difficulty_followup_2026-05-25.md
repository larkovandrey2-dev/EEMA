# Difficulty enrichment: checkpoint for 2026-05-26

## Current Production State

- The implemented runtime path remains conservative: only an active gated model may fill `NULL difficulty`.
- There is no active model now. The latest `TF-IDF + LogisticRegression` candidate was rejected.
- Stepik labels always win over model values; manually reviewed rows remain protected from ML overwrite.
- The stored TF-IDF vocabulary and classifier belong together in `ML/artifacts/difficulty/active_model.joblib` whenever a model eventually becomes active.

## Why Audit Shows `hard=128`, But Training Sees `hard=98`

The catalogue total includes manual labels, while source training intentionally excludes evaluation rows:

| Source | easy | normal | hard |
| --- | ---: | ---: | ---: |
| `stepik` / `stepik_legacy`, eligible for v1 training | 6203 | 1876 | 98 |
| `manual_holdout`, manually labelled missing-source courses | 58 | 92 | 30 |
| Catalogue total | 6261 | 1968 | 128 |

Therefore no `hard` courses disappeared: the additional 30 are the manually labelled sample and were not fed back into the original source-validation model.

## Evidence Collected On 2026-05-25

All comparisons below were read-only evaluations against the current Supabase catalogue and `ML/data/difficulty_manual_holdout_labeled.csv`.

### Current v1 model

Features: `title`, `summary`, `normalized_tags`, `workload`. Excludes `difficulty`, retrieval embedding, price, paid status, learners count, and rating.

| Evaluation | macro-F1 | easy recall | normal recall | hard recall |
| --- | ---: | ---: | ---: | ---: |
| Source 5-fold CV | 0.493364 | 0.830566 | 0.534648 | 0.081633 |
| Manual missing-source sample | 0.358699 | 0.844828 | 0.434783 | 0.000000 |

Conclusion: lowering the minimum data-count gate from `100` to `50` lets the model be evaluated with 98 source `hard` labels, but it still fails the actual quality gate.

### Looser `hard` threshold experiments

An ordinal threshold candidate can raise `hard` recall only by marking many non-hard courses as hard:

| Hard threshold setting | Manual hard recall | Manual hard precision | Predicted hard rows out of 180 |
| --- | ---: | ---: | ---: |
| Moderate (`t2=1.35`) | 0.300 | 0.273 | 33 |
| Loose (`t2=1.30`) | 0.633 | 0.260 | 73 |
| Very loose (`t2=1.25`) | 0.900 | 0.225 | 120 |

Conclusion: making `hard` softer is not safe for database backfill. It trades missing values for large numbers of wrong hard labels.

### Domain-shift experiment

The manually labelled rows are drawn from courses for which Stepik supplied no difficulty. A model trained only on Stepik-labelled courses transfers poorly to that population. Using the manual rows in cross-validation showed a possible narrow path:

| Model trained/evaluated by CV on manual missing-source rows | macro-F1 | Note |
| --- | ---: | --- |
| Word TF-IDF + balanced logistic regression | 0.601 | Better than source-trained v1 on missing rows |
| Word + character TF-IDF + balanced logistic regression | 0.576 | Did not improve overall score |

For the word TF-IDF candidate, accepting only predicted `normal` with `confidence >= 0.50` accepted `17/180` rows and all 17 were correct in this diagnostic run. This is encouraging for a selective `normal`-only model, but it is not enough evidence to activate anything:

- Coverage is small.
- There is almost no evidence for confident `easy`.
- The same 180 rows were inspected repeatedly during model selection and therefore are no longer a clean independent activation holdout.

## Recommended Next Implementation

Do not relax the existing three-class production gate. Instead, implement a separate selective enrichment experiment:

1. Treat the current labelled file `ML/data/difficulty_manual_holdout_labeled.csv` as development/training data for missing-source courses, not as final activation proof.
2. Export and label a new disjoint manual holdout of missing-source courses before any selective model can activate.
3. Train a missing-source classifier on reviewed missing-source examples.
4. Initially allow it to fill only `normal` predictions above a fixed confidence threshold; all other predictions abstain and leave `difficulty=NULL`.
5. Gate activation on the new holdout using selective metrics: accepted-count/coverage, precision among accepted rows, and zero accepted true-`hard` rows mislabelled as `normal`.
6. Give the selective artifact and provenance an explicit strategy/version so audit can distinguish it from the three-class source model.

## Tomorrow's Starting Point

No selective model code was left half-implemented on 2026-05-25. Continue by adding tests first for:

- abstention: low-confidence or non-`normal` predictions do not update a course;
- separation: training CSV IDs must not overlap the new holdout IDs;
- provenance: rows filled by the selective model identify its strategy and model version;
- activation safety: a failed selective holdout gate leaves any existing active artifact unchanged.

Until that work and a fresh independent holdout are complete, run `difficulty` only with an artifact that has already passed the existing gate; with the current reports it should perform no ML backfill.

## Implementation Decision On 2026-05-26

The selective runtime path is implemented for independently gated `easy` and `normal` outputs. Diagnostic thresholds are fixed at `easy >= 0.45` and `normal >= 0.50`; either level may activate without the other only after passing a new disjoint 180-row holdout with no accepted true-`hard` errors. Predicted `hard` and lower-confidence rows always abstain. No selective artifact is active until that new holdout is labelled and passes its gate.
