# Deployment

Author: Rayyan Anwar

## Local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env && set -a && . ./.env && set +a
python -m pytest -q
python scripts/evaluate.py
uvicorn app.main:app --port 8016        # http://127.0.0.1:8016 -> "Load sample transactions"
```
Enable auth for any shared use: `export MONITOR_API_KEYS="alice:<key>:analyst,bob:<key>:admin"`.

## Docker
`docker compose up --build` (port 8016, named volume `monitor-data` holds the SQLite file, health `/health`). Written but **not built or run** in the authoring sandbox; CI has a `docker build` job.

## Cloud
1. Build and push the image (your account). Run a **single instance** with a persistent disk: SQLite does not support multiple writers across hosts. For several replicas, swap `store.py` to PostgreSQL (not implemented).
2. Provide `MONITOR_API_KEYS` through the platform secret manager; terminate HTTPS at the load balancer; restrict network access (VPN or IAP) because transaction data is sensitive.
3. Probe `GET /health`. Back up the database volume and the exported audit CSV on a schedule; rollback = redeploy the previous image against the same volume (schema is created idempotently).
4. Not deployed by the author; no hosted demo is claimed.

## Screenshots
Load sample data, open a high-risk row and record a decision; capture into `docs/screenshots/` (none bundled).
