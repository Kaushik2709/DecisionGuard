# Checkout simulation

Run `uv run decisionguard demo` from the DecisionGuard source checkout, or pass
`--destination <new-directory>` to retain it at a chosen path. The command retains disposable
repositories under `artifacts/checkout-<id>/` by default. It never modifies an existing repository.

The fixture creates real frontend/backend/integration Git worktrees. It establishes public
`INR.major.decimal-string` and provider `INR.minor.integer` contracts. It runs initial checks,
proposes and explicitly reviews a public change, then merges disjoint edits without conflicts.
The real combined test fails with `499 != 49900`. Acknowledgement remains blocked. Updating
the frontend to send 49900, refreshing assumptions, and running task/combined checks passes.

A separate independent clone demonstrates rejecting the public change and preserving the
Decimal major-to-integer-paise adapter. All money uses decimal/integer arithmetic.
Agents and coordinator actions are deterministic simulations, with no model or API calls.

`decisionguard benchmark` adds labeled compatibility cases, lifecycle outcomes, and a real
multiprocess competing-review scenario. Its precision/recall describe planted classifications;
unknown cases are reported separately. It is not a production reliability estimate.
