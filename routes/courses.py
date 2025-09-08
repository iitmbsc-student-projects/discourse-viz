"""
Course-specific routes for the Flask application.
Handles course pages and course-related data endpoints.
"""

from flask import Blueprint, render_template
from core.utils import get_current_trimester, get_previous_trimesters
from processors.course_data_processors import get_top_10_first_responders, get_top_10_first_responders, get_trending_topics_from_useractions_df

courses_bp = Blueprint('courses', __name__)


@courses_bp.route("/<course_name>")
def course_page(course_name):
    """Main course page route"""
    course_name_original = course_name
    try:
        course_name = course_name.replace("-", "_").replace(":", "_")
        return render_template(
            'course_specific_viz.html',
            term_list_for_dropdown=get_previous_trimesters(get_current_trimester())[:2],
            course_name=course_name_original.title().replace("_", " "),
            course_name_escaped=course_name
        )
    except Exception as e:
        print(f"Error in course_page for course = {course_name}: {e}")
        return render_template(
            'course_specific_viz.html',
            course_name=course_name_original.title().replace("_", " "),
            course_name_escaped=course_name,
            error=str(e)
        )


@courses_bp.route("/get_most_frequent_first_responders/<course_name>", methods=["GET"])
def most_frequent_first_responders(course_name):
    """Fetch the most frequent first responders for a given course."""
    try:
        current_term = get_current_trimester()
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        most_freq_first_responders_list = get_top_10_first_responders(course_name)
    except Exception as e:
        most_freq_first_responders_list = []
        print(f"Encountered an error while finding most_frequent_first_responders: {e}")
    
    return render_template(
        "partials/first_responders_table.html", 
        most_freq_first_responders=most_freq_first_responders_list, 
        current_term=current_term
    )


@courses_bp.route("/most_trending_topics/<course_name>", methods=["GET"])
def most_trending_topics(course_name):
    """
    Fetch the most trending topics for a given course.
    """
    try:
        trending_scores = get_trending_topics_from_useractions_df(course_name)
        return render_template("partials/trending_topics_table.html", trending_scores=trending_scores)
    except Exception as e:
        print(f"Error fetching trending topics for {course_name}: {e}")
        return render_template("partials/trending_topics_table.html", trending_scores=[])