from flask import Flask
import os, threading
from apscheduler.schedulers.background import BackgroundScheduler

# Logging
from core.logging_config import init_logging

# Imports from other files
from core.auth import init_oauth, register_auth_routes
from application.config import Config
import core.data_loader as data_loader

# Import route blueprints
from routes import register_all_routes

# GLOBAL VARIABLES & FLAGS
init_logging()
app = Flask(__name__)
app.config.from_object(Config)

# Initialize OAuth
oauth, google = init_oauth(app)
register_auth_routes(app, google)  # GOOGLE AUTH ROUTES

# Register all blueprints
register_all_routes(app)

if __name__ == '__main__':
    # Initial load
    # Use data_loader functions instead of duplicating the logic
    df_map_category_to_id, id_username_mapping, user_actions_dictionaries = data_loader.init_minimal_data()  # Blocking: ~2 mins
    threading.Thread(target=data_loader.background_load_user_actions, daemon=True).start()

    # Schedule daily refresh jobs
    # Two separate jobs for clean separation of concerns:
    # 1. Full system reset on trimester start dates (Jan 1, May 1, Sep 1)
    # 2. Incremental updates on all other days
    scheduler = BackgroundScheduler()
    
    # JOB 1: Full System Reset (Trimester Starts Only)
    # Runs ONLY on Jan 1, May 1, Sep 1 at 3:30 AM
    # Recalculates EVERYTHING from scratch (new courses, new users, all data)
    # Recommendation: max_instances=1 prevents concurrent execution if previous run is still active
    # Recommendation: coalesce=True skips missed runs if job overlaps
    scheduler.add_job(
        func=data_loader.full_system_reset,
        trigger='cron',
        month='1,5,9',        # January, May, September only
        day='1',              # First day of month only
        hour=3,
        minute=30,
        id='trimester_full_system_reset',
        name='Full System Reset (Trimester Start)',
        max_instances=1,      # Prevent concurrent runs
        coalesce=True,        # Skip missed runs if overlapping
        replace_existing=True
    )
    
    # JOB 2: Incremental Daily Refresh (All Other Days)
    # Runs at 3:15 AM every day
    # Safety check inside refresh_all_data() skips execution on trimester start dates
    # Fetches only delta (new actions since last_refresh_date) and merges with existing data
    # Recommendation: max_instances=1 prevents race conditions with data structures
    scheduler.add_job(
        func=data_loader.refresh_all_data,
        trigger='cron',
        day='*',              # Every day
        hour=3,
        minute=15,
        id='daily_incremental_refresh',
        name='Daily Incremental Data Refresh',
        max_instances=1,      # Prevent concurrent runs
        coalesce=True,        # Skip missed runs if overlapping
        replace_existing=True
    )
    
    scheduler.start()

    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True, 
        use_reloader=False  # Prevents the scheduler from starting twice when debug mode is enabled.
    )