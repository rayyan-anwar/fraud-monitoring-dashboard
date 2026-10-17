"""FastAPI application for the Fraud Monitoring Dashboard. Author: Rayyan Anwar"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from . import __author__, __version__
from .auth import AuthError, Authenticator, Identity, parse_keys
from .data import generate_transactions
from .scorer import get_scorer
from .store import Store, StoreError

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
MAX_BYTES = 5_000_000
Status = Literal["new", "under_review", "confirmed_fraud", "false_positive", "escalated"]


class StatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status
    note: str = Field("", max_length=1000)
    expected_status: Status | None = None


def create_app(db_path: str | None = None, keys_raw: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("MONITOR_DB", "var/monitor.db")
    authn = Authenticator(parse_keys(os.environ.get("MONITOR_API_KEYS", "") if keys_raw is None else keys_raw))
    store = Store(db_path, get_scorer())
    alert_band = os.environ.get("MONITOR_ALERT_BAND", "high")
    app = FastAPI(title="Fraud Monitoring Dashboard", version=__version__,
                  description="Risk-ranked transaction queue with human review workflow and audit trail. SYNTHETIC DEMO DATA. "
                              "Author: Rayyan Anwar.", contact={"name": __author__}, license_info={"name": "MIT"})

    @app.exception_handler(StoreError)
    async def on_store_error(_: Request, exc: StoreError):
        return JSONResponse(status_code=exc.status, content={"error": {"code": "store_error", "message": exc.message}})

    @app.exception_handler(AuthError)
    async def on_auth_error(_: Request, exc: AuthError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return JSONResponse(status_code=exc.status, content={"error": {"code": "auth_error", "message": exc.message}}, headers=headers)

    def need(role: str):
        async def dep(request: Request) -> Identity:
            auth = request.headers.get("authorization", "")
            key = auth[7:].strip() if auth.lower().startswith("bearer ") else request.headers.get("x-api-key")
            return authn.require(key, role)
        return dep

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__, "author": __author__}

    @app.get("/api/info")
    def info():
        return {"name": "Fraud Monitoring Dashboard", "author": __author__, "version": __version__, "auth_required": authn.enabled,
                "data": "synthetic demo data", "intended_use": "education; alerts require human review"}

    @app.post("/api/ingest/sample")
    def ingest_sample(n: int = Query(2000, ge=100, le=20000), seed: int = Query(123, ge=0, le=10000), who: Identity = Depends(need("admin"))):
        return store.ingest(generate_transactions(n, 90, seed), who.name)

    @app.post("/api/ingest")
    async def ingest(request: Request, who: Identity = Depends(need("admin"))):
        body = await request.body()
        if len(body) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="upload too large (limit 5 MB)")
        try:
            df = pd.read_csv(io.StringIO(body.decode("utf-8-sig")))
        except Exception:
            raise StoreError(422, "could not parse CSV (UTF-8 text with a header row expected)") from None
        return await run_in_threadpool(store.ingest, df, who.name)

    @app.get("/api/transactions")
    def transactions(min_score: float | None = Query(None, ge=0, le=1), band: str | None = None, status: str | None = None,
                     channel: str | None = None, category: str | None = None, date_from: str | None = None,
                     date_to: str | None = None, customer_id: int | None = None, sort: str = "score", order: str = "desc",
                     limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), who: Identity = Depends(need("viewer"))):
        return store.list(min_score, band, status, channel, category, date_from, date_to, customer_id, sort, order, limit, offset)

    @app.get("/api/transactions/{txn_id}")
    def transaction(txn_id: str, who: Identity = Depends(need("viewer"))):
        return store.get(txn_id)

    @app.post("/api/transactions/{txn_id}/status")
    def change_status(txn_id: str, body: StatusIn, who: Identity = Depends(need("analyst"))):
        return store.set_status(txn_id, body.status, who.name, body.note, body.expected_status)

    @app.get("/api/alerts")
    def alerts(who: Identity = Depends(need("viewer"))):
        return {"band": alert_band, "items": store.alerts(alert_band)}

    @app.get("/api/stats")
    def stats(who: Identity = Depends(need("viewer"))):
        return store.stats()

    @app.get("/api/export/transactions.csv", response_class=PlainTextResponse)
    def export_transactions(status: str | None = None, band: str | None = None, who: Identity = Depends(need("viewer"))):
        return PlainTextResponse(store.export_csv("transactions", status=status, band=band), media_type="text/csv")

    @app.get("/api/export/audit.csv", response_class=PlainTextResponse)
    def export_audit(who: Identity = Depends(need("admin"))):
        return PlainTextResponse(store.export_csv("audit"), media_type="text/csv")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND)

    app.state.store = store
    return app


app = create_app()
