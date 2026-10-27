SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entities(
 kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS versions(
 contract TEXT NOT NULL, version INTEGER NOT NULL, body TEXT NOT NULL,
 PRIMARY KEY(contract,version));
CREATE TABLE IF NOT EXISTS heads(
 contract TEXT PRIMARY KEY, version INTEGER NOT NULL,
 FOREIGN KEY(contract,version) REFERENCES versions(contract,version));
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cursors(
 task TEXT PRIMARY KEY, delivered INTEGER NOT NULL DEFAULT 0, ack INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS retries(
 actor TEXT NOT NULL, key TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL,
 PRIMARY KEY(actor,key));
CREATE TRIGGER IF NOT EXISTS immutable_version_update BEFORE UPDATE ON versions
 BEGIN SELECT RAISE(ABORT,'immutable version'); END;
CREATE TRIGGER IF NOT EXISTS immutable_version_delete BEFORE DELETE ON versions
 BEGIN SELECT RAISE(ABORT,'immutable version'); END;
"""

EPOCH_TRIGGERS = [
    f"""CREATE TRIGGER IF NOT EXISTS entity_epoch_{operation.lower()}
    AFTER {operation} ON entities WHEN {reference}.kind != 'receipt'
    BEGIN UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='state_epoch'; END"""
    for operation, reference in [("INSERT", "NEW"), ("UPDATE", "NEW"), ("DELETE", "OLD")]
]

# Dedicated advisory storage deliberately has no state-epoch triggers.
V3 = [
    "CREATE INDEX IF NOT EXISTS entity_active_actor ON entities(kind,COALESCE(json_extract(body,'$.archived'),0),json_extract(body,'$.actor'))",
    "CREATE TABLE IF NOT EXISTS artifacts(digest TEXT PRIMARY KEY, body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS advisory_runs(id TEXT PRIMARY KEY, task TEXT NOT NULL, body TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS event_task_cursor ON events(task,id)",
    "CREATE INDEX IF NOT EXISTS event_notice ON events(task,json_extract(body,'$.notice_key'))",
    "CREATE INDEX IF NOT EXISTS entity_task_actor ON entities(kind,json_extract(body,'$.actor'),json_extract(body,'$.archived'))",
    "CREATE INDEX IF NOT EXISTS entity_proposal_status ON entities(kind,json_extract(body,'$.status'))",
    "CREATE INDEX IF NOT EXISTS entity_assumption_task ON entities(kind,json_extract(body,'$.task_id'))",
    "CREATE INDEX IF NOT EXISTS advisory_task ON advisory_runs(task,id)",
    "CREATE TRIGGER IF NOT EXISTS immutable_artifact_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable artifact'); END",
    "CREATE TRIGGER IF NOT EXISTS immutable_artifact_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable artifact'); END",
]
