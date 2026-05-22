from apscheduler.schedulers.blocking import BlockingScheduler
from main import run_pipeline

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

# ============================================================
# OLD SCHEDULE - 1:30 AM IST (KEPT FOR REFERENCE)
# scheduler.add_job(run_pipeline, 'cron', hour=1, minute=30)
# ============================================================

# NEW SCHEDULE - 6:00 AM IST (fetch yesterday's papers every morning)
scheduler.add_job(run_pipeline, 'cron', hour=6, minute=0)

print("Scheduler started. Pipeline runs daily at 6:00 AM IST.")

scheduler.start()