# Measuring DecisionGuard's incremental value

This workflow answers whether DecisionGuard adds enough benefit over existing engineering
checks to justify its setup and coordination effort. It does not automatically run tools,
contact participants, collect telemetry or establish product effectiveness.

## Run the local reporting slice

The included example is a **pending planted study**, with no measured observations:

```powershell
uv run decisionguard evaluation schema
uv run decisionguard evaluation plan examples/product-study/plan.json
uv run decisionguard evaluation report examples/product-study/plan.json examples/product-study/observations.json
```

The report shows planned pairs, missing arms and null rates. This is intentional. For the real
local-check fixture, run:

```powershell
uv run pytest tests/integration/test_product_study.py -q --basetemp artifacts/product-study-check
```

Its retained `study` directory contains the fixed plan, actual Python check outputs, actual
DecisionGuard validation/gate records, observations and report. The baseline catches the unit
mismatch, so incremental detections must be zero. A benign case passes both arms. This fixture
has only a combined Python assertion; it is not a full schema/codegen baseline or live-agent trial.
It does not perform a separate integration, so escaped-defect rates remain unknown.

The [strong baseline fixture](../examples/strong-baseline/README.md) adds actual pinned OpenAPI
codegen, strict TypeScript, JSON Schema, provider contract and HTTP checks. Its paired study still
reports zero incremental catches on the planted unit mismatch. See [ALPHA_WORKFLOW.md](ALPHA_WORKFLOW.md)
for `evaluation kit`, consented feedback/pricing-interest fields, setup and recovery procedures.

## Fix the protocol before measuring

1. Copy the example into a new local study archive. Use pseudonymous participant/repository IDs;
   scrub secrets from evidence. Preserve each starting checkout and final repaired source.
2. Configure and record a strong baseline: actual schema validation, actual codegen/type checks,
   consumer/provider contract tests and actual combined integration tests. Include commands,
   tool versions and configurations in the plan check descriptions. Both arms get the same checks.
   The treatment adds reviewed declarations, polling, invalidation and gates.
3. Include representative semantic changes, ordinary schema changes, benign changes and undeclared
   assumptions. Include cases the baseline already catches. Have reviewers label expected outcomes
   without seeing tool results; retain their rationale as hashed label evidence. Use `unknown` for
   insufficient context. No reviewer independence is inferred from a supplied name.
4. Fix the participant/case list, selection method, question and success criteria. Inspect the plan,
   retain its digest and timestamp in an external study archive before execution. The local tool
   checks timestamps/digests but cannot prove that registration actually preceded the experiment.
5. Run matched tasks from the same starting revision. Counterbalance arm order or use separate
   participants to reduce learning effects. Record failures, unsupported checks and abandonment.
   Retain outputs even when results weaken the product hypothesis.

Suggested pilot recruitment and duration remain in [the external checklist](ADVISORY_EVALUATION.md).
Use its 10 developers / 3+ repositories / two weeks as a planned target, never as completed data.
Preregister concrete limits for acceptable setup time, benign block rate and added elapsed time,
alongside required defect/rework benefit and voluntary continuation. Choose limits for the target
workflow; the example's criteria are protocol examples, not universal approval thresholds.

## Record observations

Use `evaluation schema` for the authoritative field definitions. An observations document has
`schema_version: 1`, the inspected `plan_sha256`, and optional `observations`, `setup`, `feedback`
arrays. Every completed arm needs a case/participant/method, planned source revision, aware
`observed_at`, each planned check status and at least one evidence reference:

```json
{"path":"logs/arm-output.json","sha256":"REPLACE_WITH_FILE_SHA256"}
```

Evidence is relative to its containing plan or observations file. Hash the exact retained bytes
(for example with PowerShell `Get-FileHash -Algorithm SHA256`, lowercasing the digest). There is
no command execution or log-content interpretation. Measurements are operator-recorded, and the
report explicitly says hashes do not attest their truth. Keep the archive separate from captured
application source. No secrets, provider keys or private code need to enter the report.

Measure detection from change availability, elapsed time through the observation endpoint, actual
rework seconds and active tool-operation overhead. Avoid double-counting overlapping intervals.
Leave unmeasured values null/absent. Report whether actual downstream integration was correct,
defective, not performed or unknown. A blocked task does not imply a prevented production defect.
Record baseline and treatment setup separately, including failed setup time. Feedback is explicit
yes/no/undecided/withdrew, backed by a consented local response artifact; missing replies stay missing.

## Interpret the report

- Inspect exclusions and missing measurements before comparing outcomes. Unknown or unavailable
  runs are never credited as successes. Completed-pair metrics alone can be biased by attrition.
- Both additional DecisionGuard detections and baseline-only detections are reported. A baseline
  detection is not an incremental discovery. Benign blocks expose coordination cost.
- Detection-time deltas cover **only pairs with detection in both arms**, so use detection counts
  alongside timing. Other paired deltas use only pairs with both measurements; negative means
  less time with DecisionGuard. Setup is reported separately from task elapsed time.
- Rates apply to recorded eligible pairs with known outcomes; their numerators/denominators and
  unknowns are explicit. Multiple participants repeating a case are not independent source cases.
- Planted or convenience cases cannot establish incident frequency. Even consecutive sampling
  needs an audited sampling window and missing-case review; this tool estimates no population rate.
- Neither a large sample nor favourable arithmetic approves effectiveness or release. Review net
  benefit, representativeness, order effects, participant continuation and baseline quality manually.

External competitor runs must use documented pinned configurations and retained outputs. The
CLI executes none of them. Live Jev classification has a separate evaluation protocol; strong
classification metrics do not establish product utility or give advice authority over gates.
