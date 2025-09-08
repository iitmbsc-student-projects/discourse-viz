"""
API endpoints for the Flask application.
Handles API-specific routes and data endpoints.
"""

from flask import Blueprint, render_template, jsonify
import core.data_loader as data_loader
from constants import (
    foundation_courses, 
    diploma_programming_courses, 
    diploma_data_science_courses, 
    degree_courses
)
from core.utils import get_current_trimester

api_bp = Blueprint('api', __name__)


@api_bp.route('/')
def index():
    """Main index page route"""
    latest_term = get_current_trimester()
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    
    return render_template(
        'index.html', 
        foundation_courses=foundation_courses,
        diploma_programming_courses=diploma_programming_courses,
        diploma_data_science_courses=diploma_data_science_courses,
        degree_courses=degree_courses,
        overall_discourse_charts=list(user_actions_dictionaries.keys()),  # LIST of terms (current and past)
        latest_chart=latest_term
    )


@api_bp.route('/loading-status')
def loading_status():
    """API endpoint to check if user actions data is loaded"""
    user_actions_loaded = data_loader.get_user_actions_loaded()
    return jsonify({"loaded": user_actions_loaded})