"""
Course-specific routes for the Flask application.
Handles course pages and course-related data endpoints.
"""

from core.auth import login_required
from flask import Blueprint, render_template
from core.utils import get_current_trimester, get_previous_trimesters
from processors.course_data_processors import get_top_10_first_responders, get_top_10_first_responders, get_trending_topics_from_useractions_df
from core.logging_config import get_logger

logger_trending = get_logger("viz.trending")
logger_course = get_logger("viz.course_top10")

courses_bp = Blueprint('courses', __name__)


@courses_bp.route("/<course_name>")
@login_required
def course_page(course_name):
    """Main course page route"""
    course_name_original = course_name
    try:
        course_name = course_name.replace("-", "_").replace(":", "_")
        logger_course.info(f"Rendering course page | function: course_page | course: {course_name}", extra={"course": course_name})
        return render_template(
            'course_specific_viz.html',
            term_list_for_dropdown=get_previous_trimesters(get_current_trimester())[:3],
            course_name=course_name_original.title().replace("_", " "),
            course_name_escaped=course_name
        )
    except Exception as e:
        logger_course.exception(f"Error rendering course page | function: course_page | course: {course_name} | Error: {e}", extra={"course": course_name})
        return render_template(
            'course_specific_viz.html',
            course_name=course_name_original.title().replace("_", " "),
            course_name_escaped=course_name,
            error=str(e)
        )


@courses_bp.route("/get_most_frequent_first_responders/<course_name>", methods=["GET"])
@login_required
def most_frequent_first_responders(course_name):
    """Fetch the most frequent first responders for a given course."""
    try:
        current_term = get_current_trimester()
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        logger_course.info(f"Fetching top first responders | function: most_frequent_first_responders | course: {course_name} | term: {current_term}", extra={"course": course_name, "term": current_term})
        most_freq_first_responders_list = get_top_10_first_responders(course_name)
    except Exception as e:
        most_freq_first_responders_list = []
        logger_course.exception(f"Error finding first responders | function: most_frequent_first_responders | course: {course_name} | Error: {e}", extra={"course": course_name})
    
    return render_template(
        "partials/first_responders_table.html", 
        most_freq_first_responders=most_freq_first_responders_list, 
        current_term=current_term
    )


@courses_bp.route("/most_trending_topics/<course_name>", methods=["GET"])
@login_required
def most_trending_topics(course_name):
    """
    Fetch the most trending topics for a given course.
    """
    try:
        logger_trending.info(f"Fetching trending topics | function: most_trending_topics | course: {course_name}", extra={"course": course_name})
        trending_scores = get_trending_topics_from_useractions_df(course_name)
        return render_template("partials/trending_topics_table.html", trending_scores=trending_scores)
    except Exception as e:
        logger_trending.exception(f"Error fetching trending topics | function: most_trending_topics | course: {course_name} | Error: {e}", extra={"course": course_name})
        return render_template("partials/trending_topics_table.html", trending_scores=[])