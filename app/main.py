"""FastAPI application for LOTO6 analyzer with auto-scraping and caching."""

import os
import logging
import threading
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app import db, scraper, analyzer, predictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("loto6")

# --- in-memory cache keyed by latest_round ---
_cache_lock = threading.Lock()
_analysis_cache: dict = {}  # {"round": int, "data": ...}
_predictions_cache: dict = {}  # {(round, seed): ...}
_last_fetch_at: str = ""
_last_fetch_ok: bool = False
_last_source: str = ""


def _invalidate_cache():
    global _analysis_cache, _predictions_cache
    with _cache_lock:
        _analysis_cache = {}
        _predictions_cache = {}


def get_analysis() -> dict:
    global _analysis_cache
    current_round = db.latest_round() or 0
    with _cache_lock:
        if _analysis_cache.get("round") == current_round and current_round > 0:
            return _analysis_cache["data"]
    draws = db.all_draws()
    result = analyzer.compute(draws)
    with _cache_lock:
        _analysis_cache = {"round": current_round, "data": result}
    return result


def _do_fetch():
    global _last_fetch_at, _last_fetch_ok, _last_source
    try:
        rows, source = scraper.fetch_all()
        if rows:
            added = db.insert_rows(rows)
            log.info("scrape OK: source=%s fetched=%d added=%d", source, len(rows), added)
            if added > 0:
                _invalidate_cache()
        _last_fetch_ok = True
        _last_source = source
    except Exception as e:
        log.error("scrape failed: %s", e)
        _last_fetch_ok = False
        _last_source = "error"
    _last_fetch_at = datetime.now().isoformat(timespec="seconds")


def _startup_fetch():
    """Run initial fetch in a daemon thread so it doesn't block startup."""
    t = threading.Thread(target=_do_fetch, daemon=True)
    t.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _startup_fetch()
    # setup scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        sched = BackgroundScheduler(daemon=True)
        sched.add_job(_do_fetch, CronTrigger(hour=22, minute=0, timezone="Asia/Tokyo"))
        sched.start()
        log.info("scheduler started: daily 22:00 JST")
    except ImportError:
        log.warning("apscheduler not installed; skipping scheduled fetch")
    yield


app = FastAPI(title="LOTO6 Analyzer", lifespan=lifespan)

# --- static files ---
web_dir = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(web_dir):
    app.mount("/web", StaticFiles(directory=web_dir), name="web")


@app.get("/")
def root():
    index = os.path.join(web_dir, "index.html")
    return FileResponse(index)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return {
        "rows": db.count_rows(),
        "latest_round": db.latest_round(),
        "latest_date": (db.latest_draw() or {}).get("date"),
        "last_fetch_at": _last_fetch_at,
        "last_fetch_ok": _last_fetch_ok,
        "source": _last_source,
    }


@app.get("/api/latest")
def latest():
    draw = db.latest_draw()
    if not draw:
        return {"error": "no data"}
    return draw


@app.get("/api/expectation")
def expectation():
    return get_analysis()


@app.get("/api/predictions")
def predictions():
    analysis = get_analysis()
    return predictor.generate(analysis)


@app.post("/api/refresh")
def refresh():
    _do_fetch()
    return {
        "rows": db.count_rows(),
        "latest_round": db.latest_round(),
        "last_fetch_ok": _last_fetch_ok,
    }
