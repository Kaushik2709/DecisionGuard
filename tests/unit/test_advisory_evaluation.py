import pytest

from decisionguard.domain.errors import GuardError
from decisionguard.reports.advisory_evaluation import EvaluationDataset, evaluate
from decisionguard.storage.sqlite import dumps


def dataset():
    return EvaluationDataset.model_validate(
        {
            "schema_version": 1,
            "fixture_only": True,
            "cases": [
                {
                    "id": "case-1",
                    "repository": "heldout-repo",
                    "change_family": "family-a",
                    "split": "heldout",
                    "expected": "possible_contract_impact",
                    "reviewed_by": "fixture-reviewer",
                    "advisory_id": "a" * 64,
                    "deterministic_prediction": "no_impact_indicated",
                    "heuristic_prediction": "no_impact_indicated",
                },
                {
                    "id": "case-2",
                    "repository": "heldout-repo",
                    "change_family": "family-b",
                    "split": "heldout",
                    "expected": "possible_contract_impact",
                    "reviewed_by": "fixture-reviewer",
                    "advisory_id": "b" * 64,
                    "deterministic_prediction": "insufficient_context",
                    "heuristic_prediction": "insufficient_context",
                },
            ],
        }
    )


def test_unavailable_predictions_count_as_misses_without_promotion(project):
    service, _ = project
    with service.store.transaction() as db:
        for token, status in (("a", "available"), ("b", "unavailable")):
            body = {
                "model": "jev-1.13.0",
                "status": status,
                "answers": {"candidate_0": {"label": "possible_contract_impact"}},
            }
            db.execute(
                "INSERT INTO advisory_runs VALUES(?,?,?)", (token * 64, "worker", dumps(body))
            )
    result = evaluate(service, dataset())
    assert result["calls_made"] == 0 and not result["promotion_approved"]
    assert result["metrics"]["jev"]["recall"] == 0.5
    assert result["metrics"]["jev"]["abstentions"] == 1
    assert result["incremental_discoveries"] == 1
    assert not result["sample_size_target_met"]


def test_repository_split_leakage_is_rejected(project):
    service, _ = project
    data = dataset().model_dump()
    data["cases"][0]["split"] = "development"
    with pytest.raises(GuardError, match="leakage"):
        evaluate(service, EvaluationDataset.model_validate(data))


def test_duplicate_prediction_cannot_inflate_sample_size(project):
    service, _ = project
    data = dataset().model_dump()
    data["cases"][1]["advisory_id"] = data["cases"][0]["advisory_id"]
    with pytest.raises(GuardError, match="Duplicate prediction"):
        evaluate(service, EvaluationDataset.model_validate(data))
