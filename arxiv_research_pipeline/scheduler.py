from apscheduler.schedulers.blocking import BlockingScheduler
from main import run_pipeline

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

scheduler.add_job(run_pipeline, 'cron', hour=1, minute=30)

print("Scheduler started. Pipeline runs daily at 1:30 AM IST.")

scheduler.start()