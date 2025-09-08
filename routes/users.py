"""
User-related routes for the Flask application.
Handles user search, user details, and user-specific functionality.
"""

from flask import Blueprint, render_template, jsonify
from user_summary.user_summary_functions import get_user_summary, get_basic_metrics, get_top_categories, get_liked_by_users

users_bp = Blueprint('users', __name__)


@users_bp.route('/search_user')
def search_user():
    """Route invoked when user clicks on "Search User" button"""
    return render_template('user.html')


@users_bp.route("/user_details/<user_name>", methods=["GET"])
def get_user_details(user_name):
    """
    This function fetches the user details for a given username.
    This route is invoked when user clicks on the "search" button on the "search_user" page
    """
    try:
        summary_data = get_user_summary(user_name)
        basic_metrics = get_basic_metrics(summary_data)
        top_categories = get_top_categories(summary_data)
        most_liked_by = get_liked_by_users(summary_data)
        
        return jsonify({
            'basic_metrics': basic_metrics.to_dict(orient="records"),
            'top_categories': top_categories.to_dict(orient="records"),
            'most_liked_by': most_liked_by.to_dict(orient="records"),
        })
    except Exception as e:
        print(f"Error fetching user details for {user_name}: {e}")
        return jsonify({
            'error': f'Could not fetch details for user: {user_name}',
            'basic_metrics': [],
            'top_categories': [],
            'most_liked_by': []
        }), 500