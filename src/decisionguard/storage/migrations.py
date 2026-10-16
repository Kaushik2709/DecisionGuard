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
