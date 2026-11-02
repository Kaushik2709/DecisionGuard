# Graphify project knowledge

Start project navigation with `graphify-out/GRAPH_REPORT.md` and
`graphify-out/graph.json`, then verify relevant relationships against source and
behavioral tests. The generated map is local navigation assistance.

## Generate or refresh

Run from `D:\DecisionGuard` in PowerShell with the installed Graphify CLI:

```powershell
$env:PYTHONUTF8 = '1'
graphify extract . --code-only --no-cluster --max-workers 1
graphify cluster-only . --no-label
```

Both commands must succeed. This uses local AST extraction and numbered community
labels without model calls or API keys. Graphify 0.9.65 was used for the verified
run. The project's `.graphifyignore` excludes credentials, state, dependencies,
caches, distributions, generated graphs, and disposable worktrees under `artifacts/`.
The generated directory is also ignored by Git.

The code-only scope includes supported source, tests, scripts, examples and config
files. It skips prose documents, papers and images; read canonical specifications
directly. Inferred edges and community membership need source verification.
Regenerate after source changes; the report's commit ID alone cannot detect
uncommitted changes.

## Use

Open `graphify-out/graph.html` in a browser. Search for `Service`, select its class
result, and use the community checkboxes to reduce visual clutter. The viewer loads
vis-network 9.1.6 from unpkg with an integrity hash, so it needs network access to
that CDN. The JSON graph, report and CLI queries remain usable without the viewer.

If a browser restricts local files, serve only the generated directory:

```powershell
.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory graphify-out
```

Then open `http://127.0.0.1:8766/graph.html`. Stop the server with Ctrl+C.

```powershell
graphify explain 'src/decisionguard/application/services.py::Service'
graphify query 'gate validation' --budget 700
```

`Service` alone is ambiguous because the CLI also defines `service()`. Use a
qualified name for `explain`. Query output announces truncation when its budget
is too small; narrow the query or increase the budget.

## Initial verification - 2026-10-30

- Extraction succeeded: 91 indexed code/config files, 666 raw nodes, 3,106 raw edges.
- Clustering succeeded: 715 nodes, 2,942 edges and 26 numbered communities.
- Final edges: 2,570 EXTRACTED and 372 INFERRED; no model token usage.
- Data checks passed: unique node IDs, valid edge endpoints, existing source paths,
  excluded local paths absent, all 78 project Python files represented in the manifest.
  Nodes reference 85 files; indexing a file need not produce a symbol node.
- Qualified `explain` returned the Service class at `services.py:L43`, and the gate
  query returned source locations and an explicit budget-truncation notice.
- Browser check passed over loopback HTTP: graph canvas, search, Service inspection
  and community filtering (715 visible nodes -> 0 -> 715). The only browser resource
  error was an absent optional favicon; the viewer library loaded successfully.
- Evidence: `graphify-out/verification.json`, `viewer-verified.png`, `browser-logs/`.

Graphify warns about older globally installed Claude/Gemini skill copies; these
warnings did not prevent extraction, queries or rendering. Global settings and
skills were not changed. No application behavior changed or runtime test suite ran.

Official reference: <https://github.com/Graphify-Labs/graphify>.

The runtime/release hardening refresh later on 2026-10-30 generated 760 nodes,
2,929 edges and 33 communities. See `graphify-out/verification.json` for the latest
indexed-file fingerprints and structural checks. The retained viewer screenshot
and browser checks above describe the initial 715-node graph.
