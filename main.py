import os, json, glob, logging, asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from scraper import run_scraper
from fetcher import fetch_leads
from exporter import export_to_excel
from config_manager import load_config, save_config, get_default_config

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Universal Form Bot API")
scheduler = AsyncIOScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory run history (last 50 runs)
run_history = []


async def full_cycle(config: dict = None):
    cfg = config or load_config()
    if not cfg.get("target_url"):
        log.warning("No target_url configured — skipping cycle.")
        return

    run_entry = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "started_at": datetime.now().isoformat(),
        "target": cfg["target_url"],
        "status": "running",
        "forms_found": 0,
        "forms_submitted": 0,
        "leads_fetched": 0,
        "excel_path": None,
        "error": None,
    }
    run_history.insert(0, run_entry)
    if len(run_history) > 50:
        run_history.pop()

    log.info(f"=== Cycle start — {cfg['target_url']} ===")
    try:
        # Step 1: Scrape & submit forms
        result = await run_scraper(cfg)
        run_entry["forms_found"]     = result.get("forms_found", 0)
        run_entry["forms_submitted"] = result.get("forms_submitted", 0)

        # Step 2: Fetch leads from backend
        leads = fetch_leads(cfg)
        run_entry["leads_fetched"] = len(leads)

        # Step 3: Export
        if leads:
            path = export_to_excel(leads, cfg)
            run_entry["excel_path"] = path
            log.info(f"Exported {len(leads)} leads → {path}")

        run_entry["status"] = "success"
    except Exception as e:
        run_entry["status"] = "error"
        run_entry["error"]  = str(e)
        log.error(f"Cycle failed: {e}", exc_info=True)

    run_entry["finished_at"] = datetime.now().isoformat()
    log.info(f"=== Cycle end — status: {run_entry['status']} ===")
    return run_entry


@app.on_event("startup")
async def startup():
    cfg = load_config()
    interval = cfg.get("interval_hours", 6)
    if cfg.get("auto_run", False):
        scheduler.add_job(full_cycle, IntervalTrigger(hours=interval), id="bot_job")
        scheduler.start()
        log.info(f"Scheduler started — every {interval}h")


@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown()


# ─── Config endpoints ──────────────────────────────────────────────────────────

@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def update_config(body: dict):
    save_config(body)
    # Restart scheduler with new interval if auto_run changed
    if scheduler.running:
        scheduler.remove_all_jobs()
        if body.get("auto_run"):
            scheduler.add_job(full_cycle, IntervalTrigger(hours=body.get("interval_hours", 6)), id="bot_job")
    elif body.get("auto_run"):
        scheduler.add_job(full_cycle, IntervalTrigger(hours=body.get("interval_hours", 6)), id="bot_job")
        scheduler.start()
    return {"status": "saved"}

@app.get("/api/config/default")
def default_config():
    return get_default_config()


# ─── Bot control endpoints ─────────────────────────────────────────────────────

@app.post("/api/run")
async def manual_run(background_tasks: BackgroundTasks):
    cfg = load_config()
    if not cfg.get("target_url"):
        return JSONResponse(status_code=400, content={"error": "No target_url set. Configure the bot first."})
    background_tasks.add_task(full_cycle, cfg)
    return {"status": "started", "message": "Bot cycle launched in background"}

@app.get("/api/status")
def get_status():
    cfg = load_config()
    return {
        "scheduler_running": scheduler.running,
        "auto_run": cfg.get("auto_run", False),
        "interval_hours": cfg.get("interval_hours", 6),
        "target_url": cfg.get("target_url", ""),
        "total_runs": len(run_history),
        "last_run": run_history[0] if run_history else None,
    }

@app.get("/api/history")
def get_history():
    return run_history

@app.get("/api/download")
def download_latest():
    files = sorted(glob.glob("/tmp/leads_*.xlsx"), reverse=True)
    if not files:
        return JSONResponse(status_code=404, content={"error": "No Excel file yet. Run the bot first."})
    return FileResponse(
        path=files[0],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(files[0])
    )

@app.get("/api/leads")
def get_leads_preview():
    """Preview last fetched leads (from config backend)."""
    cfg = load_config()
    if not cfg.get("target_url"):
        return []
    try:
        return fetch_leads(cfg)[:50]  # preview max 50
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
