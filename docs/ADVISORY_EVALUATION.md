# Advisory evaluation and production gates

Product utility is evaluated separately through the offline paired-study workflow in
[PRODUCT_EVALUATION.md](PRODUCT_EVALUATION.md). Advisory prediction metrics do not establish
incremental value over schema/codegen plus contract/integration tests.

Jev is experimental, opt-in and advisory only. No live classifier accuracy, latency, pricing,
production benefit or competitive superiority is established by the offline mock tests.

Prepare 200 independently reviewed cases: 80 impactful, 80 benign, 40 insufficient-context.
Use 80 development and 120 held-out examples, separated by repository and change-family ID.
Do not split paraphrases or variants of one change across the boundary. Reviewers should
label impacts without seeing model predictions. Record the source revision and supplied
context alongside the dataset in your own evaluation archive.

The local command reads stored responses; it makes no requests:

```
decisionguard --root <repository> advice evaluate <labels.json>
```

Dataset format (`cases` must be nonempty):

```json
{
  "schema_version": 1,
  "fixture_only": false,
  "cases": [{
    "id": "reviewed-case-001",
    "repository": "repository-a",
    "change_family": "checkout-conversion-001",
    "split": "heldout",
    "expected": "possible_contract_impact",
    "reviewed_by": "reviewer-identifier",
    "advisory_id": "REPLACE_WITH_64_CHARACTER_STORED_ADVISORY_ID",
    "candidate": "candidate_0",
    "deterministic_prediction": "no_impact_indicated",
    "heuristic_prediction": "insufficient_context"
  }]
}
```

Labels are `possible_contract_impact`, `no_impact_indicated`, `insufficient_context`.
Baseline/heuristic predictions are operator-supplied evidence, not automatically measured by
the evaluator. Capture them from equivalent runs and retain raw artifacts. Missing/unavailable
model results count as abstentions and as misses for actual positive cases. Sample size alone
does not approve promotion. Compare deterministic DecisionGuard, a documented local heuristic,
and Jev on exactly the same changes and context. Also run the original worktree/test baseline,
Clash and Foremerge with pinned versions and their documented configurations. Report unsupported
capabilities, setup failures and unknowns separately rather than crediting them as success.

Promotion requires held-out advisory precision >=90%, recall >=85%, benign warning rate <=5%,
successful-request p95 <=2s with timeouts separately counted, and useful incremental discoveries
beyond both baselines. Record provider token usage and actual billed charges; do not infer cost
or domain accuracy from confidence. An optional feature does not become gate authority when it
meets these targets. A future authority change needs a separate design and review.

## External release checklist

- 10 developers, 3+ full-stack repositories, 2-week opt-in pilot; >=8 completed evaluations
  and >=6 choosing to continue. No automatic telemetry or invented participant evidence.
- Run an 8-hour concurrency soak and large-history benchmarks; retain p50/p95, peak memory,
  lock contention, database/WAL growth, recovery and restore results.
- Run remote Windows/Linux CI, installed-wheel CLI/MCP tests and retained v1/v2 migration fixtures.
- Review dependency licenses/SBOM, configure a private security-reporting channel and protected
  release environment, and verify the public package/brand before publishing.
- Publication, hosted portal, automatic agent wakeup and A2A integration remain separate work.
