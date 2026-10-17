"""Tests for auth, store (ingest/filter/workflow/audit/export), scorer and (if installed) the HTTP API.

Author: Rayyan Anwar
"""
import csv
import io
import os
import sqlite3
import tempfile
import unittest

import pandas as pd

from app.auth import AuthError, Authenticator, Identity, parse_keys
from app.data import generate_transactions
from app.scorer import get_scorer
from app.store import STATUSES, TRANSITIONS, Store, StoreError, csv_safe

DF = generate_transactions(1500, 90, 123)


def fresh_store():
    d = tempfile.mkdtemp()
    s = Store(os.path.join(d, "t.db"), get_scorer())
    s.ingest(DF)
    return s


class TestAuth(unittest.TestCase):
    def test_parse_and_roles(self):
        keys = parse_keys("alice:k1:analyst, bob:k2:admin,carol:k3:viewer")
        a = Authenticator(keys)
        self.assertEqual(a.require("k2", "admin"), Identity("bob", "admin"))
        self.assertEqual(a.require("k1", "viewer").name, "alice")
        with self.assertRaises(AuthError) as cm:
            a.require("k3", "analyst")
        self.assertEqual(cm.exception.status, 403)
        for bad in (None, "", "nope"):
            with self.assertRaises(AuthError) as cm:
                a.require(bad, "viewer")
            self.assertEqual(cm.exception.status, 401)

    def test_disabled_auth_is_local_admin(self):
        a = Authenticator(parse_keys(""))
        self.assertFalse(a.enabled)
        self.assertEqual(a.require(None, "admin"), Identity("local-user", "admin"))

    def test_bad_key_config_rejected(self):
        for raw in ("alice:k1", "alice:k1:root", "a:k:viewer,b:k:admin", ":k:viewer"):
            with self.assertRaises(ValueError, msg=raw):
                parse_keys(raw)


class TestScorer(unittest.TestCase):
    def test_bands_and_ranking(self):
        sc = get_scorer()
        self.assertGreater(sc.high, sc.medium)
        s = sc.score(DF)
        self.assertEqual(len(s), len(DF))
        fr = DF["is_fraud"] == 1
        self.assertGreater(s[fr.to_numpy()].mean(), s[~fr.to_numpy()].mean())
        self.assertEqual(sc.band(1.0), "high")
        self.assertEqual(sc.band(0.0), "low")


class TestIngest(unittest.TestCase):
    def test_ingest_counts_and_dedup(self):
        s = fresh_store()
        self.assertEqual(s.stats()["transactions"], 1500)
        again = s.ingest(DF)
        self.assertEqual((again["inserted"], again["already_present"]), (0, 1500))
        self.assertEqual(s.stats()["transactions"], 1500)

    def test_rejections_are_reported_by_reason(self):
        d = DF.iloc[:10].copy()
        d.loc[d.index[0], "amount"] = -5
        d.loc[d.index[1], "channel"] = "mail"
        d["timestamp"] = d["timestamp"].astype(object)
        d.loc[d.index[2], "timestamp"] = "garbage"
        d.loc[d.index[3], "merchant_category"] = "casino"
        d = pd.concat([d, d.iloc[[5]]])
        s = Store(os.path.join(tempfile.mkdtemp(), "r.db"), get_scorer())
        r = s.ingest(d)
        self.assertEqual(r["inserted"], 6)
        self.assertEqual(r["rejected"], {"invalid timestamp": 1, "invalid amount": 1, "unknown merchant_category": 1,
                                         "unknown channel": 1, "duplicate txn_id in batch": 1})

    def test_missing_columns_and_all_invalid(self):
        s = Store(os.path.join(tempfile.mkdtemp(), "m.db"), get_scorer())
        with self.assertRaises(StoreError) as cm:
            s.ingest(DF.drop(columns=["amount", "channel"]))
        self.assertEqual(cm.exception.status, 422)
        bad = DF.iloc[:3].copy()
        bad["amount"] = -1
        self.assertEqual(s.ingest(bad)["inserted"], 0)

    def test_accepts_foreign_column_name_and_optional_customer(self):
        s = Store(os.path.join(tempfile.mkdtemp(), "f.db"), get_scorer())
        r = s.ingest(DF.iloc[:5].drop(columns=["customer_id", "is_fraud"]))
        self.assertEqual(r["inserted"], 5)


class TestQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = fresh_store()

    def test_default_is_risk_ranked(self):
        items = self.s.list(limit=100)["items"]
        scores = [i["score"] for i in items]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_filters_combine(self):
        r = self.s.list(band="high", channel="online", min_score=0.95, limit=200)
        self.assertGreater(r["total"], 0)
        self.assertTrue(all(i["band"] == "high" and i["channel"] == "online" and i["score"] >= 0.95 for i in r["items"]))
        r2 = self.s.list(date_from="2025-02-01", date_to="2025-02-28T23:59:59", limit=200)
        self.assertTrue(all("2025-02-01" <= i["timestamp"][:10] <= "2025-02-28" for i in r2["items"]))
        cid = r["items"][0]["customer_id"]
        self.assertTrue(all(i["customer_id"] == cid for i in self.s.list(customer_id=cid)["items"]))

    def test_pagination_consistent(self):
        a, b = self.s.list(limit=10, offset=0)["items"], self.s.list(limit=10, offset=10)["items"]
        self.assertEqual(len({i["txn_id"] for i in a + b}), 20)

    def test_invalid_query_parameters(self):
        for kw in ({"sort": "id; DROP TABLE transactions"}, {"order": "sideways"}, {"limit": 0}, {"limit": 201},
                   {"offset": -1}, {"band": "extreme"}, {"status": "lost"}, {"channel": "x"}, {"category": "y"}):
            with self.assertRaises(StoreError, msg=str(kw)):
                self.s.list(**kw)
        self.assertGreater(self.s.list(sort="amount", order="asc")["total"], 0)

    def test_sql_injection_attempt_in_filter_values_is_inert(self):
        r = self.s.list(date_from="x'; DROP TABLE transactions; --")  # bound as a plain string: matches nothing
        self.assertEqual(r["total"], 0)
        self.assertEqual(self.s.stats()["transactions"], 1500)

    def test_alerts_exclude_closed_items(self):
        s = fresh_store()
        top = s.alerts("high")[0]["txn_id"]
        s.set_status(top, "false_positive", "alice", "legitimate purchase")
        self.assertNotIn(top, [a["txn_id"] for a in s.alerts("high")])
        self.assertTrue(all(a["band"] == "high" for a in s.alerts("high")))
        self.assertGreaterEqual(len(s.alerts("medium")), len(s.alerts("high")))


class TestWorkflow(unittest.TestCase):
    def test_happy_path_and_history(self):
        s = fresh_store()
        t = s.alerts()[0]["txn_id"]
        s.set_status(t, "under_review", "alice")
        d = s.set_status(t, "confirmed_fraud", "bob", "customer confirmed by phone")
        self.assertEqual(d["status"], "confirmed_fraud")
        self.assertEqual([h["new_status"] for h in d["history"]], ["under_review", "confirmed_fraud"])
        self.assertEqual([h["reviewer"] for h in d["history"]], ["alice", "bob"])

    def test_invalid_transitions_and_validation(self):
        s = fresh_store()
        t = s.alerts()[0]["txn_id"]
        cases = [(t, "bogus", "x", 422), (t, "confirmed_fraud", "", 422), (t, "confirmed_fraud", "n" * 1001, 422),
                 ("missing-id", "under_review", "", 404)]
        for tid, st, note, code in cases:
            with self.assertRaises(StoreError, msg=st) as cm:
                s.set_status(tid, st, "alice", note)
            self.assertEqual(cm.exception.status, code)
        s.set_status(t, "confirmed_fraud", "alice", "ok")
        with self.assertRaises(StoreError) as cm:
            s.set_status(t, "under_review", "alice")
        self.assertEqual(cm.exception.status, 409)

    def test_optimistic_concurrency_conflict(self):
        s = fresh_store()
        t = s.alerts()[0]["txn_id"]
        s.set_status(t, "under_review", "alice", expected_status="new")
        with self.assertRaises(StoreError) as cm:
            s.set_status(t, "escalated", "bob", "needs senior", expected_status="new")
        self.assertEqual(cm.exception.status, 409)
        self.assertEqual(s.get(t)["status"], "under_review")

    def test_audit_is_append_only(self):
        s = fresh_store()
        t = s.alerts()[0]["txn_id"]
        s.set_status(t, "under_review", "alice")
        with s.conn() as c:
            with self.assertRaises(sqlite3.DatabaseError):
                c.execute("UPDATE audit SET reviewer='mallory'")
        with s.conn() as c:
            with self.assertRaises(sqlite3.DatabaseError):
                c.execute("DELETE FROM audit")
        self.assertEqual(s.stats()["audit_rows"], 2)  # ingest + one status change

    def test_random_walk_matches_model_and_audit_count(self):
        import random
        rng = random.Random(0)
        s = fresh_store()
        ids = [i["txn_id"] for i in s.list(limit=40)["items"]]
        model = {i: "new" for i in ids}
        ok = 0
        for _ in range(300):
            t, new = rng.choice(ids), rng.choice(STATUSES)
            allowed = new in TRANSITIONS[model[t]]
            try:
                s.set_status(t, new, "r", "note")
                self.assertTrue(allowed)
                model[t] = new
                ok += 1
            except StoreError:
                self.assertFalse(allowed)
        self.assertEqual({i: s.get(i)["status"] for i in ids}, model)
        self.assertEqual(s.stats()["audit_rows"], 1 + ok)

    def test_reviewed_precision(self):
        s = fresh_store()
        a, b, c = [x["txn_id"] for x in s.alerts()[:3]]
        s.set_status(a, "confirmed_fraud", "r", "n")
        s.set_status(b, "false_positive", "r", "n")
        s.set_status(c, "confirmed_fraud", "r", "n")
        self.assertAlmostEqual(s.stats()["reviewed_precision"], 2 / 3)


class TestExport(unittest.TestCase):
    def test_csv_formula_injection_is_neutralised(self):
        self.assertEqual(csv_safe("=1+1"), "'=1+1")
        self.assertEqual(csv_safe("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(csv_safe("normal"), "normal")
        self.assertEqual(csv_safe(5), 5)
        s = fresh_store()
        t = s.alerts()[0]["txn_id"]
        s.set_status(t, "false_positive", "=cmd|' /C calc'!A0", "=HYPERLINK(\"http://x\")")
        rows = list(csv.reader(io.StringIO(s.export_csv("audit"))))
        last = rows[-1]
        self.assertTrue(last[3].startswith("'=") and last[7].startswith("'="))
        self.assertEqual(rows[0][:3], ["id", "ts", "txn_id"])

    def test_transaction_export_respects_filters(self):
        s = fresh_store()
        rows = list(csv.DictReader(io.StringIO(s.export_csv("transactions", band="high"))))
        self.assertTrue(rows and all(r["band"] == "high" for r in rows))


try:
    import fastapi  # noqa: F401
    import httpx  # noqa: F401
    HAVE_API = True
except ImportError:
    HAVE_API = False


@unittest.skipUnless(HAVE_API, "fastapi/httpx not installed - API tests are skipped, not passed")
class TestApi(unittest.TestCase):
    def client(self, keys=""):
        from fastapi.testclient import TestClient
        from app.main import create_app
        return TestClient(create_app(os.path.join(tempfile.mkdtemp(), "api.db"), keys))

    def test_open_mode_flow(self):
        c = self.client()
        self.assertEqual(c.get("/health").json()["author"], "Rayyan Anwar")
        self.assertIn("Rayyan Anwar", c.get("/").text)
        self.assertEqual(c.post("/api/ingest/sample", params={"n": 300}).json()["inserted"], 300)
        t = c.get("/api/alerts").json()["items"][0]["txn_id"]
        r = c.post(f"/api/transactions/{t}/status", json={"status": "under_review"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(c.post(f"/api/transactions/{t}/status", json={"status": "confirmed_fraud"}).status_code, 422)
        self.assertEqual(c.post(f"/api/transactions/{t}/status", json={"status": "new"}).status_code, 409)
        self.assertEqual(c.get("/api/transactions/nope").status_code, 404)
        self.assertIn("id,ts", c.get("/api/export/audit.csv").text)

    def test_roles_enforced(self):
        c = self.client("v:kv:viewer,a:ka:analyst,m:km:admin")
        self.assertEqual(c.get("/api/stats").status_code, 401)
        self.assertEqual(c.post("/api/ingest/sample", headers={"Authorization": "Bearer ka"}).status_code, 403)
        self.assertEqual(c.post("/api/ingest/sample", params={"n": 200}, headers={"X-API-Key": "km"}).status_code, 200)
        t = c.get("/api/alerts", headers={"Authorization": "Bearer kv"}).json()["items"][0]["txn_id"]
        self.assertEqual(c.post(f"/api/transactions/{t}/status", json={"status": "under_review"}, headers={"Authorization": "Bearer kv"}).status_code, 403)
        ok = c.post(f"/api/transactions/{t}/status", json={"status": "under_review"}, headers={"Authorization": "Bearer ka"})
        self.assertEqual(ok.json()["history"][-1]["reviewer"], "a")
        self.assertEqual(c.get("/api/export/audit.csv", headers={"Authorization": "Bearer ka"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
