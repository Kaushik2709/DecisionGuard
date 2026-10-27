import json

import httpx
import pytest
from conftest import CONTRACT, key

from decisionguard.application.advisories import classify, list_advisories, parse_response, preview
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.advisories import AdviceCandidate, AdviceRequest
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import TaskMutation


def request():
    return AdviceRequest(
        task_id="worker",
        model="jev-1.13.0",
        candidates=[AdviceCandidate(contract=CONTRACT, paths=["code.py"])],
    )


def answer(label="possible_contract_impact"):
    labels = ("possible_contract_impact", "no_impact_indicated", "insufficient_context")
    return {
        "model": "jev-1.13.0",
        "answers": {
            "candidate_0": {
                "type": "choice",
                "choice": label,
                "probabilities": {k: float(k == label) for k in labels},
                "confidence": 1.0,
            }
        },
        "usage": {"input_tokens": 100, "output_tokens": 10},
    }


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    monkeypatch.setenv("DECISIONGUARD_JEV_API_KEY", "test-only-not-a-real-key")


def test_advice_is_explicit_idempotent_and_cannot_change_gate(project, monkeypatch):
    service, _ = project
    validate(service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    before = gate(service, ["worker"])["receipt"]
    saved = preview(service, request())
    with service.store.connect() as db:
        epoch = db.execute("SELECT value FROM meta WHERE key='state_epoch'").fetchone()[0]
    calls = []

    def handler(outbound):
        calls.append(json.loads(outbound.content))
        return httpx.Response(200, json=answer())

    transport(monkeypatch, handler)
    first = classify(service, saved)
    assert classify(service, saved) == first
    assert len(calls) == 1
    assert first["advisory"]["status"] == "available"
    assert first["advisory"]["answers"]["candidate_0"]["label"] == "possible_contract_impact"
    after = gate(service, ["worker"])["receipt"]
    assert after["passed"] == before["passed"]
    assert after["findings"] == before["findings"]
    with service.store.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='state_epoch'").fetchone()[0] == epoch
    assert list_advisories(service, "worker")["advisories"][0]["freshness"] == "current"


def test_preview_redacts_and_mcp_cannot_prepare_or_submit(project):
    service, root = project
    (root / "code.py").write_text("api_key='sk_12345678901234567890'\n")
    saved = preview(service, request())
    assert "12345678901234567890" not in json.dumps(saved["payload"])
    actor = Service(service.directory, session_actor="worker")
    with pytest.raises(GuardError):
        preview(actor, request())
    with pytest.raises(GuardError):
        classify(actor, saved)


@pytest.mark.parametrize("failure", ["timeout", "malformed", "wrong_model", "http_error"])
def test_failures_never_become_clear_and_are_not_retried(project, monkeypatch, failure):
    service, _ = project
    saved = preview(service, request())
    calls = []

    def handler(outbound):
        calls.append(outbound)
        if failure == "timeout":
            raise httpx.ReadTimeout("test")
        if failure == "http_error":
            return httpx.Response(503)
        body = answer()
        if failure == "wrong_model":
            body["model"] = "different-model"
        else:
            body["answers"]["candidate_0"]["probabilities"] = {"safe": 1}
        return httpx.Response(200, json=body)

    transport(monkeypatch, handler)
    assert classify(service, saved)["advisory"]["status"] == "unavailable"
    assert classify(service, saved)["advisory"]["status"] == "unavailable"
    assert len(calls) == 1


def test_source_change_invalidates_preview_before_and_after_call(project, monkeypatch):
    service, root = project
    saved = preview(service, request())

    def handler(outbound):
        (root / "code.py").write_text("amount = 49900\n")
        return httpx.Response(200, json=answer("no_impact_indicated"))

    transport(monkeypatch, handler)
    assert classify(service, saved)["advisory"]["status"] == "stale"
    with pytest.raises(GuardError) as error:
        classify(service, saved)
    assert error.value.code == "SOURCE_CHANGED"


def test_negative_advice_cannot_clear_a_pending_gate(project, monkeypatch):
    from conftest import proposal

    service, _ = project
    proposal(service)
    before = gate(service, ["worker"])["receipt"]
    assert not before["passed"]
    transport(monkeypatch, lambda outbound: httpx.Response(200, json=answer("no_impact_indicated")))
    assert classify(service, preview(service, request()))["advisory"]["status"] == "available"
    after = gate(service, ["worker"])["receipt"]
    assert not after["passed"] and after["findings"] == before["findings"]


@pytest.mark.parametrize("mutation", ["nan", "sum", "confidence", "choice"])
def test_response_validation_is_strict(mutation):
    body = answer()
    item = body["answers"]["candidate_0"]
    if mutation == "nan":
        item["confidence"] = float("nan")
    elif mutation == "sum":
        item["probabilities"]["insufficient_context"] = 0.5
    elif mutation == "confidence":
        item["confidence"] = 0.5
    else:
        item["choice"] = "no_impact_indicated"
    with pytest.raises(GuardError):
        parse_response(body, "jev-1.13.0", {"candidate_0"})
