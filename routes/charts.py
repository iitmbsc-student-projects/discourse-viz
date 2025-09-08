"""
Chart-related routes for the Flask application.
Handles all chart generation and visualization endpoints.
"""

from flask import Blueprint, request, render_template, jsonify
import pandas as pd
from datetime import datetime, timedelta

import core.data_loader as data_loader
from core.utils import get_current_trimester
from processors.functions_to_get_charts import (
    create_stacked_bar_chart_for_overall_engagement,
    create_stacked_bar_chart_for_course_specific_engagement,
    create_empty_chart_in_case_of_errors
)
from processors.functions_to_get_charts import create_weekwise_engagement

charts_bp = Blueprint('charts', __name__)


def generate_chart_for_overall_engagement(term):
    """Generate overall engagement chart for a specific term."""
    try:
        user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
        id_username_mapping = data_loader.get_id_username_mapping()
        unnormalized_df = user_actions_dictionaries[term]["overall"]["unnormalized_scores"]
        unnormalized_df = unnormalized_df[unnormalized_df["user_id"] > 0]
        top_10_users = pd.DataFrame(unnormalized_df.head(10))
        top_10_users = top_10_users.merge(id_username_mapping, on="user_id")
        chart = create_stacked_bar_chart_for_overall_engagement(top_10_users, term=term)
        return chart
    except Exception as e:
        print(f"Error generating overall engagement chart: {e}")
        chart = create_empty_chart_in_case_of_errors(
            message="The chart may not have been loaded properly, please wait for some time and then refresh. Contact support if issue persists."
        )
        return chart


def get_users_engagement_chart(course, user_list, term="t1-2025"):
    """
    Returns the course-specific chart of a specific set of users; uses unnormalised dataframe
    """
    user_list = [name.lower().strip() for name in user_list]
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    relevant_df = user_actions_dictionaries[term][course]["unnormalized_scores"]
    relevant_df = relevant_df[(relevant_df["acting_username"].str.lower()).isin(user_list)]
    
    if not relevant_df.empty:
        chart = create_stacked_bar_chart_for_course_specific_engagement(relevant_df, course)
        return chart
    else:
        return create_empty_chart_in_case_of_errors(
            message="None of the users from the list was found, please provide a new set of users."
        )


def get_top_10_users_chart(term, subject):
    """
    Returns the course & term specific chart of top-10 most active users; uses log-normalised dataframe
    """
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    log_normalized_df = user_actions_dictionaries[term][subject]["log_normalized_scores"]

    if not log_normalized_df.empty:
        top_10 = log_normalized_df.head(10).acting_username.to_list()
        raw_metrics = user_actions_dictionaries[term][subject]["raw_metrics"]
        raw_metrics = raw_metrics[raw_metrics.acting_username.isin(top_10)]
        highest_activity_chart = create_stacked_bar_chart_for_course_specific_engagement(
            raw_metrics=raw_metrics, subject=subject
        )
    else:
        highest_activity_chart = create_empty_chart_in_case_of_errors(
            message="Course was either not offered this term OR it had extremely less interactions on discourse"
        )
    
    return highest_activity_chart


@charts_bp.route('/get_chart')
def get_overall_discourse_chart():
    """Used to get the Overall Discourse Charts on the home page"""
    user_actions_loaded = data_loader.get_user_actions_loaded()
    if not user_actions_loaded:
        return "<h3 style='color:violet'>Data is still loading. Once the background data fetching is completed, the chart will automatically be rendered.<br>Kindly wait for a few minutes!</h3>"
    
    term = request.args.get('chart')
    if term:
        chart_html = generate_chart_for_overall_engagement(term).to_html()
        return chart_html
    else:
        return "<h2>No chart selected</h2>"


@charts_bp.route("/<course_name>/top_users_chart/<term>")
def top_users_chart(course_name, term):
    """Endpoint that returns only the top users chart"""
    try:
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        top_10_users_chart = get_top_10_users_chart(term=term, subject=course_name)
        return top_10_users_chart.to_html()
    except Exception as e:
        print(f"Error in top_users_chart for course = {course_name}: {e}")
        empty_chart = create_empty_chart_in_case_of_errors(
            message="Could not load top users chart; the course might not have been offered"
        )
        return empty_chart.to_html()


@charts_bp.route("/<course_name>/weekwise_chart/<term>")
def weekwise_chart(course_name, term):
    """Endpoint that returns only the weekwise engagement chart"""
    try:
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
        user_actions_df = user_actions_dictionaries[term][course_name]["user_actions_df"]
        weekwise_engagement_chart = create_weekwise_engagement(user_actions_df)
        return weekwise_engagement_chart.to_html()
    except Exception as e:
        print(f"Error in weekwise_chart for course = {course_name}: {e}")
        empty_chart = create_empty_chart_in_case_of_errors(
            message="Could not load weekly engagement chart; the course might not have been offered"
        )
        return empty_chart.to_html()


@charts_bp.route("/<course_name>/get_specific_users_stat", methods=["POST"])
def specific_users_stat(course_name):
    """Returns a chart showing activity of a set of users"""
    try:
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        user_list = request.form.get("user_list")
        selected_term = request.form.get("selected_term")
        
        if not user_list:
            return jsonify({"error": "No usernames provided."}), 400

        user_list = tuple(user_list.split(","))
        chart = get_users_engagement_chart(course_name, user_list, term=selected_term)
        return chart.to_html()
    except Exception as e:
        print(f"Error: {e} in specific_users_stat function for the route /{course_name}/get_specific_users_stat")
        return jsonify({"error": "Internal error occurred."}), 500