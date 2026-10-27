# TypeScript / Python checkout fixture

This is a disposable integration fixture, not a production payment application. Python's
standard-library HTTP server listens only on loopback; the provider is a local function.
The fixed bearer value is a fixture marker, not a real credential. Node 24 executes erasable
TypeScript directly; this does not constitute a separate TypeScript type-check.

Run `python verify.py` here. It starts an ephemeral Python API, runs the TypeScript client,
checks authentication, JSON response shape and the exact provider amount, then stops the API.
No npm installation, model key, internet connection or payment provider is used.

The regression copies these files into a disposable directory. Baseline: client sends 499
rupees and API converts to 49900 paise. Change only `client.ts` to send 49900: the check fails
with 4990000. Change the API to accept paise directly: it passes again. This demonstrates a
cross-language semantic bug; it is not a live-agent effectiveness trial.

## Using contracts in a disposable repository

Copy this directory to a separate scratch repository, initialize and commit it with Git, then
initialize DecisionGuard with a reviewed runner (`argv`: absolute Python path plus `verify.py`).
Register a CLI task `checkout` with its worktree root and paths `["."]`. This deliberately broad
scope belongs only to the small fixture; use narrow scopes in real projects.

Keep request/preview files outside captured source (or in the shared state directory).

```
decisionguard --root <scratch-repository> contracts scan <scan-request.json>
```

Publication JSON contains `actor`, `idempotency_key`, `scan` (the scan-request object),
`preview_digest` (returned by scan), `expected_versions` (all four contract identities mapped
to 0 initially), and `rationale`. Submit using `contracts propose <publish-request.json>`.
Each returned proposal still needs separate authorized `review`; nothing is accepted by scan.
Declare the task's assumptions against accepted versions before validation/gating.

`scan-request.json` binds the request, response and authentication contracts and explicitly
states the business unit. Producer/consumer IDs are reviewed context; agents must still declare
their implementation assumptions. Source code and OpenAPI are not automatically synchronized.

## Optional Jev advisory

The example model ID is illustrative; verify availability with your provider. Use a versioned
model, not `latest`. After inspecting the actual outbound preview:

```
decisionguard --root <scratch-repository> advice preview <advice-request.json> <new-preview.json>
decisionguard --root <scratch-repository> advice classify <new-preview.json>
decisionguard --root <scratch-repository> advice list checkout
```

Only the last two file arguments on `advice preview` are local paths. `classify` performs a
paid external request using `DECISIONGUARD_JEV_API_KEY`; the preview and normal workflow never
call a model. Never put that variable's value in a request file. Redaction is best effort.
Repeated classification of the same preview does not send again. To deliberately retry after
a failure, increment `attempt`, prepare a new preview and inspect it before submission.

Advice cannot accept contracts, run tests or clear the deterministic gate. Missing context,
outage or low certainty cannot prove compatibility.
