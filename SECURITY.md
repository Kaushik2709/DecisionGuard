# Security policy

This repository contains an unreleased local developer tool. A stable supported-version or
maintainer response-time guarantee has not been established. Do not present local tests or
the MIT license as a security certification.

## Reporting

A verified private reporting channel must be configured before public release. If the public
repository enables GitHub private vulnerability reporting, use its Security tab. Until an
owner-controlled private channel is confirmed, do not put secrets, customer data, private source
or exploitable production details in a public issue. No email address or monitored SLA is implied.

## Trust boundaries

- Same-user trusted local repositories, configuration and SQLite state. Shell access can bypass
  MCP actor restrictions; this project is not an agent sandbox or multi-tenant authorization layer.
- Only reviewed local runner argv executes. MCP does not accept commands or invoke runners.
- Shared SQLite must stay on a local filesystem. Stop all legacy/current sessions before
  migration or restoration; retain backups and regenerate evidence.
- Windows Job Objects / POSIX process groups manage ordinary descendants. Forced POSIX supervisor
  death or deliberately escaped daemons require additional containment; no sandbox guarantee.
- Optional Jev is explicit and advisory-only. Inspect its exact outbound payload; redaction is
  best effort. Keep DECISIONGUARD_JEV_API_KEY outside JSON, source, history and diagnostic output.
- Passing tests prove only the configured checks against the recorded source/decision state.

See docs/SECURITY_AUDIT.md for historical reproductions and remediations, and tasks.md for
remaining recovery, soak, independent evaluation and release gates.
