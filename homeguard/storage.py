"""SQLite persistence with parameterized queries and MQTT message deduplication."""
import json
import sqlite3
from contextlib import contextmanager
from .config import DB_PATH
from .protocol import timestamp

class Store:
    def __init__(self, path=DB_PATH):
        self.path = str(path)
        from pathlib import Path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, received_at TEXT NOT NULL,
                    topic TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS data (
                    id INTEGER PRIMARY KEY, message_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL, device TEXT NOT NULL,
                    metric TEXT NOT NULL, value REAL NOT NULL,
                    unit TEXT NOT NULL, UNIQUE(message_id, metric));
                CREATE TABLE IF NOT EXISTS iot_devices (
                    name TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    last_updated TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL, source TEXT NOT NULL,
                    message TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS data_metric_time ON data(metric, timestamp);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def record(self, topic, payload, metrics=()):
        """Persist a validated packet and its measurements in one transaction."""
        with self.connection() as db:
            cur = db.execute("INSERT OR IGNORE INTO messages VALUES (?,?,?,?)",
                (payload["id"], timestamp(), topic, json.dumps(payload)))
            if cur.rowcount == 0:
                return False
            db.execute("INSERT INTO iot_devices VALUES (?,?,?,?) ON CONFLICT(name) "
                "DO UPDATE SET kind=excluded.kind,last_updated=excluded.last_updated,state=excluded.state",
                (payload["device"], payload["kind"], payload["timestamp"], json.dumps(payload)))
            db.executemany("INSERT INTO data(message_id,timestamp,device,metric,value,unit) VALUES (?,?,?,?,?,?)",
                [(payload["id"],payload["timestamp"],payload["device"],m,v,u) for m,v,u in metrics])
            return True

    def event(self, severity, source, text):
        with self.connection() as db:
            cur = db.execute("INSERT INTO events(timestamp,severity,source,message) VALUES (?,?,?,?)",
                             (timestamp(),severity,source,text))
            return cur.lastrowid

    def history(self, metric="temperature", limit=120):
        with self.connection() as db:
            rows = db.execute("SELECT timestamp,value FROM data WHERE metric=? ORDER BY id DESC LIMIT ?",
                              (metric, int(limit))).fetchall()
        return [dict(row) for row in reversed(rows)]

    def events(self, limit=100):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(limit,))]

    def counts(self):
        with self.connection() as db:
            return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("messages","data","iot_devices","events")}
