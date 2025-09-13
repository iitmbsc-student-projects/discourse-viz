from flask import Flask
import os, threading
from apscheduler.schedulers.background import BackgroundScheduler

# Imports from other files
from core.auth import init_oauth, register_auth_routes
from application.config import Config
import core.data_loader as data_loader

# Import route blueprints
from routes import register_all_routes

# GLOBAL VARIABLES & FLAGS
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

    # Schedule daily refresh
    scheduler = BackgroundScheduler()
    scheduler.add_job(data_loader.refresh_all_data, 'cron', hour=3, minute=30)  # refresh data every day at 3:30 am
    scheduler.start()

    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True, 
        use_reloader=False  # Prevents the scheduler from starting twice when debug mode is enabled.
    )