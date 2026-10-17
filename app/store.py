"""SQLite-backed transaction queue with review workflow and an append-only audit trail.

Author: Rayyan Anwar
"""
from __future__ import annotations

import csv
import io
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import pandas as pd

from .data import CATEGORIES, CHANNELS
from .scorer import Scorer

STATUSES = ("new", "under_review", "confirmed_fraud", "false_positive", "escalated")
TRANSITIONS = {
    "new": {"under_review", "confirmed_fraud", "false_positive", "escalated"},
    "under_review": {"confirmed_fraud", "false_positive", "escalated"},
    "escalated": {"under_review", "confirmed_fraud", "false_positive"},
    "false_positive": {"under_review"},
    "confirmed_fraud": set(),
}
OPEN = ("new", "under_review", "escalated")
REQUIRED = ("txn_id", "timestamp", "amount", "merchant_category", "channel", "foreign", "new_device", "txn_count_1h", "account_age_days")
SORTS = {"score": "score", "amount": "amount", "timestamp": "timestamp", "updated": "updated_at"}
MAX_NOTE = 1000
MAX_BATCH_ROWS = 100_000
SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions(
  txn_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, customer_id INTEGER, amount REAL NOT NULL, merchant_category TEXT NOT NULL,
  channel TEXT NOT NULL, foreign_txn INTEGER NOT NULL, new_device INTEGER NOT NULL, txn_count_1h INTEGER NOT NULL,
  account_age_days INTEGER NOT NULL, score REAL NOT NULL, band TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
  updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_score ON transactions(score DESC);
CREATE INDEX IF NOT EXISTS ix_status ON transactions(status);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, txn_id TEXT, reviewer TEXT NOT NULL, action TEXT NOT NULL,
  old_status TEXT, new_status TEXT, note TEXT);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
"""


class StoreError(Exception):
    """status: 404 not found, 409 conflict, 422 invalid input."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def csv_safe(v):
    """Neutralise spreadsheet formula injection in exported cells."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


class Store:
    def __init__(self, path: str, scorer: Scorer):
        self.path, self.scorer = path, scorer
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    # ---- ingest ---------------------------------------------------------
    def ingest(self, df: pd.DataFrame, reviewer: str = "system") -> dict:
        df = df.reset_index(drop=True)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "foreign" in df.columns and "foreign_txn" not in df.columns:
            df = df.rename(columns={"foreign": "foreign_txn"})
        missing = [c for c in REQUIRED if c.replace("foreign", "foreign_txn") not in df.columns and c not in df.columns]
        if missing:
            raise StoreError(422, f"missing required columns: {missing}")
        if len(df) > MAX_BATCH_ROWS:
            raise StoreError(422, f"batch too large (limit {MAX_BATCH_ROWS} rows)")
        if "customer_id" not in df.columns:
            df["customer_id"] = 0
        reasons: dict[str, int] = {}

        def reject(mask, why):
            n = int(mask.sum())
            if n:
                reasons[why] = reasons.get(why, 0) + n
            return mask

        ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_localize(None)
        amount = pd.to_numeric(df["amount"], errors="coerce")
        nums = {c: pd.to_numeric(df[c], errors="coerce") for c in ("foreign_txn", "new_device", "txn_count_1h", "account_age_days", "customer_id")}
        bad = reject(ts.isna(), "invalid timestamp")
        bad |= reject(~(amount > 0) | (amount > 1_000_000), "invalid amount")
        bad |= reject(~df["merchant_category"].isin(CATEGORIES), "unknown merchant_category")
        bad |= reject(~df["channel"].isin(CHANNELS), "unknown channel")
        bad |= reject(~nums["foreign_txn"].isin([0, 1]) | ~nums["new_device"].isin([0, 1]), "flags must be 0/1")
        bad |= reject(~(nums["txn_count_1h"] >= 1) | ~(nums["account_age_days"] >= 0), "invalid count fields")
        bad |= reject(df["txn_id"].isna() | (df["txn_id"].astype(str).str.len() == 0), "missing txn_id")
        dup_in_batch = reject(df["txn_id"].astype(str).duplicated(keep="first") & ~bad, "duplicate txn_id in batch")
        ok = df[~(bad | dup_in_batch)].copy()
        if ok.empty:
            return {"received": len(df), "inserted": 0, "rejected": reasons, "already_present": 0}
        clean = pd.DataFrame({
            "txn_id": ok["txn_id"].astype(str), "timestamp": ts[ok.index],
            "customer_id": nums["customer_id"][ok.index].fillna(0).astype(int), "amount": amount[ok.index],
            "merchant_category": ok["merchant_category"], "channel": ok["channel"], "foreign": nums["foreign_txn"][ok.index].astype(int),
            "new_device": nums["new_device"][ok.index].astype(int), "txn_count_1h": nums["txn_count_1h"][ok.index].astype(int),
            "account_age_days": nums["account_age_days"][ok.index].astype(int)})
        scores = self.scorer.score(clean)
        stamp = now()
        rows = [(r.txn_id, r.timestamp.isoformat(), int(r.customer_id), float(r.amount), r.merchant_category, r.channel, int(r.foreign),
                 int(r.new_device), int(r.txn_count_1h), int(r.account_age_days), float(s), self.scorer.band(float(s)), stamp)
                for r, s in zip(clean.itertuples(index=False), scores)]
        with self.conn() as c:
            before = c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            c.executemany("INSERT OR IGNORE INTO transactions(txn_id,timestamp,customer_id,amount,merchant_category,channel,foreign_txn,"
                          "new_device,txn_count_1h,account_age_days,score,band,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            inserted = c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] - before
            c.execute("INSERT INTO audit(ts,txn_id,reviewer,action,note) VALUES(?,?,?,?,?)",
                      (stamp, None, reviewer, "ingest", f"received {len(df)}, inserted {inserted}"))
        return {"received": len(df), "inserted": inserted, "rejected": reasons, "already_present": len(rows) - inserted}

    # ---- queries --------------------------------------------------------
    def list(self, min_score=None, band=None, status=None, channel=None, category=None, date_from=None, date_to=None,
             customer_id=None, sort="score", order="desc", limit=50, offset=0) -> dict:
        if sort not in SORTS:
            raise StoreError(422, f"sort must be one of {sorted(SORTS)}")
        if order not in ("asc", "desc"):
            raise StoreError(422, "order must be asc or desc")
        if not 1 <= limit <= 200 or offset < 0:
            raise StoreError(422, "limit must be 1-200 and offset >= 0")
        for name, val, allowed in (("band", band, ("low", "medium", "high")), ("status", status, STATUSES),
                                   ("channel", channel, CHANNELS), ("category", category, CATEGORIES)):
            if val is not None and val not in allowed:
                raise StoreError(422, f"{name} must be one of {list(allowed)}")
        where, args = [], []
        if min_score is not None:
            where.append("score >= ?"); args.append(float(min_score))
        for col, val in (("band", band), ("status", status), ("channel", channel), ("merchant_category", category)):
            if val is not None:
                where.append(f"{col} = ?"); args.append(val)
        if date_from:
            where.append("timestamp >= ?"); args.append(str(date_from))
        if date_to:
            where.append("timestamp <= ?"); args.append(str(date_to))
        if customer_id is not None:
            where.append("customer_id = ?"); args.append(int(customer_id))
        w = (" WHERE " + " AND ".join(where)) if where else ""
        with self.conn() as c:
            total = c.execute(f"SELECT COUNT(*) FROM transactions{w}", args).fetchone()[0]
            rows = c.execute(f"SELECT * FROM transactions{w} ORDER BY {SORTS[sort]} {order.upper()}, txn_id LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        return {"total": total, "limit": limit, "offset": offset, "items": [dict(r) for r in rows]}

    def alerts(self, band: str = "high", limit: int = 200) -> list[dict]:
        bands = ("high",) if band == "high" else ("high", "medium")
        q = f"SELECT * FROM transactions WHERE band IN ({','.join('?' * len(bands))}) AND status IN ('new','under_review','escalated') ORDER BY score DESC, txn_id LIMIT ?"
        with self.conn() as c:
            return [dict(r) for r in c.execute(q, list(bands) + [limit]).fetchall()]

    def get(self, txn_id: str) -> dict:
        with self.conn() as c:
            r = c.execute("SELECT * FROM transactions WHERE txn_id = ?", (txn_id,)).fetchone()
            if r is None:
                raise StoreError(404, "transaction not found")
            hist = c.execute("SELECT ts,reviewer,action,old_status,new_status,note FROM audit WHERE txn_id = ? ORDER BY id", (txn_id,)).fetchall()
        return {**dict(r), "history": [dict(h) for h in hist]}

    def stats(self) -> dict:
        with self.conn() as c:
            by_status = {r[0]: r[1] for r in c.execute("SELECT status, COUNT(*) FROM transactions GROUP BY status")}
            by_band = {r[0]: r[1] for r in c.execute("SELECT band, COUNT(*) FROM transactions GROUP BY band")}
            open_alerts = c.execute("SELECT COUNT(*) FROM transactions WHERE band='high' AND status IN ('new','under_review','escalated')").fetchone()[0]
            audit_rows = c.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        conf, fp = by_status.get("confirmed_fraud", 0), by_status.get("false_positive", 0)
        return {"transactions": sum(by_status.values()), "by_status": {s: by_status.get(s, 0) for s in STATUSES},
                "by_band": {b: by_band.get(b, 0) for b in ("high", "medium", "low")}, "open_high_alerts": open_alerts,
                "reviewed_precision": (conf / (conf + fp)) if conf + fp else None, "audit_rows": audit_rows,
                "note": "reviewed_precision = confirmed / (confirmed + false positive) among reviewed items only; it is biased toward the alert queue."}

    # ---- workflow -------------------------------------------------------
    def set_status(self, txn_id: str, new_status: str, reviewer: str, note: str = "", expected_status: str | None = None) -> dict:
        if new_status not in STATUSES:
            raise StoreError(422, f"status must be one of {list(STATUSES)}")
        note = (note or "").strip()
        if len(note) > MAX_NOTE:
            raise StoreError(422, f"note must be at most {MAX_NOTE} characters")
        if new_status != "under_review" and not note:
            raise StoreError(422, "a note is required for this decision")
        with self.conn() as c:
            c.execute("BEGIN IMMEDIATE")
            r = c.execute("SELECT status FROM transactions WHERE txn_id = ?", (txn_id,)).fetchone()
            if r is None:
                raise StoreError(404, "transaction not found")
            old = r["status"]
            if expected_status is not None and expected_status != old:
                raise StoreError(409, f"status changed by someone else (now '{old}')")
            if new_status not in TRANSITIONS[old]:
                raise StoreError(409, f"transition {old} -> {new_status} is not allowed")
            stamp = now()
            c.execute("UPDATE transactions SET status = ?, updated_at = ? WHERE txn_id = ?", (new_status, stamp, txn_id))
            c.execute("INSERT INTO audit(ts,txn_id,reviewer,action,old_status,new_status,note) VALUES(?,?,?,?,?,?,?)",
                      (stamp, txn_id, reviewer, "status_change", old, new_status, note))
        return self.get(txn_id)

    # ---- export ---------------------------------------------------------
    def export_csv(self, table: str = "audit", **list_filters) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        if table == "audit":
            with self.conn() as c:
                cur = c.execute("SELECT id,ts,txn_id,reviewer,action,old_status,new_status,note FROM audit ORDER BY id")
                w.writerow([d[0] for d in cur.description])
                for r in cur:
                    w.writerow([csv_safe(v) for v in tuple(r)])
        else:
            rows = self.list(limit=200, **list_filters)["items"]
            cols = ["txn_id", "timestamp", "customer_id", "amount", "merchant_category", "channel", "score", "band", "status", "updated_at"]
            w.writerow(cols)
            for r in rows:
                w.writerow([csv_safe(r[c]) for c in cols])
        return buf.getvalue()
