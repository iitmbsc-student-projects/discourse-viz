"""
Routes package for the Flask application.
This package contains all route definitions organized by functionality.
"""

from .charts import charts_bp
from .courses import courses_bp
from .users import users_bp
from .api import api_bp

def register_all_routes(app):
    """Register all blueprint routes with the Flask application."""
    app.register_blueprint(charts_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(api_bp)