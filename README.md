# Fraud Monitoring Dashboard

**Author: Rayyan Anwar** — AI/ML Engineer | Researcher | Technology Manager | Software Developer

A risk-ranked transaction queue with filters, high-risk alerts, a **human review workflow** (allowed status transitions, mandatory notes, optimistic concurrency), **role-based access**, and an **append-only audit trail** you can export. Demo data is synthetic.

> **Synthetic data, human review required.** Scores are relative risk signals, not fraud determinations. The system never takes automatic action. Read [docs/MODEL_CARD.md](docs/MODEL_CARD.md) before adapting it.

## Implemented vs optional
| Feature | Status |
|---|---|
| Validated CSV/sample ingest with rejection reasons, scoring, bands | Implemented, tested |
| Filtering, sorting, pagination, alerts, stats | Implemented, tested |
| Status workflow with transition rules, notes, conflict detection | Implemented, tested (incl. randomised model check) |
| Append-only audit trail (SQLite triggers) and CSV export with formula-injection protection | Implemented, tested |
| API-key roles: viewer, analyst, admin | Implemented, tested at core level; HTTP enforcement tests written but **not executed in the authoring sandbox** |
| Browser dashboard | Implemented; JavaScript syntax-checked only |
| PostgreSQL, SSO, retraining/drift monitoring, fairness audit, notifications | Not implemented |

## Results (committed run, `results/RESULTS.md`; synthetic data)
Top-50 queue precision 1.00 (random queue 0.019); high-band precision 0.67 and recall 0.43 at about 2.7 alerts per day; 3000 randomised workflow operations matched an independent model with an exact audit count; 20,000 rows ingest in about 0.3 s. See [docs/EVALUATION.md](docs/EVALUATION.md) for caveats.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --port 8016      # open http://127.0.0.1:8016 and load sample transactions
```
With auth disabled (empty `MONITOR_API_KEYS`) every visitor is an admin: **local demos only**. Endpoints: `GET /api/transactions`, `/api/alerts`, `/api/stats`, `/api/export/*.csv`; `POST /api/ingest`, `/api/ingest/sample`, `/api/transactions/{id}/status`; docs at `/docs`.

## Documentation
[Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md) · [System card](docs/MODEL_CARD.md) · [Deployment](docs/DEPLOYMENT.md)

## Testing status
22 tests executed and passing (`python -m unittest`); 2 HTTP API tests skipped in the authoring sandbox (FastAPI/httpx unavailable) and run in CI. Docker not built; Ruff not run. A test run caught a real bug (batches with duplicate index labels failed to ingest); it is fixed and tested.

## Known limitations
SQLite single node; uncalibrated scores; synthetic features only; no drift monitoring, fairness audit or PII controls; reviewed precision is biased toward the alert queue.

## GitHub repository metadata
- **Description:** Risk-ranked fraud review queue with human workflow, role-based access and an append-only audit trail (synthetic demo data).
- **Topics:** `fraud-detection`, `dashboard`, `human-in-the-loop`, `audit-log`, `fastapi`, `sqlite`, `responsible-ai`, `python`

## License
MIT © Rayyan Anwar. See [LICENSE](LICENSE).
