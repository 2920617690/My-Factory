"""Gateway request links only; official model events remain owned by B."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Links:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS links (task_id TEXT PRIMARY KEY, upstream_id TEXT UNIQUE NOT NULL, input_json TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload_json TEXT, error TEXT)')
        path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM links WHERE task_id=?', (id,)).fetchone()
        if row is None:
            raise KeyError(id)
        return dict(row)

    def reserve(self, id, body):
        serialized = json.dumps(body, ensure_ascii=False, sort_keys=True)
        upstream = 'MF-DEMO-'+id.removeprefix('FDN-')
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO links(task_id,upstream_id,input_json,state,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                (id, upstream, serialized, 'pending', now(), now()))
            row = dict(db.execute('SELECT * FROM links WHERE task_id=?', (id,)).fetchone())
        if row['input_json'] != serialized:
            raise ValueError('Task ID already has different inputs')
        return row

    def update(self, id, *, payload=None, error=None):
        with self.connect() as db:
            if payload is not None:
                db.execute('UPDATE links SET state=?,payload_json=?,error=NULL,updated_at=? WHERE task_id=?',
                    (payload['state'], json.dumps(payload, ensure_ascii=False), now(), id))
            else:
                db.execute('UPDATE links SET error=?,updated_at=? WHERE task_id=?', (error, now(), id))

    def rows(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM links ORDER BY created_at DESC LIMIT 30')]
