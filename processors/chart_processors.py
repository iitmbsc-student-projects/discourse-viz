"""
Chart processing functions for generating various visualizations.
Contains business logic for chart generation and data processing.
"""

import pandas as pd
import core.data_loader as data_loader
from processors.functions_to_get_charts import (
    create_stacked_bar_chart_for_overall_engagement,
    create_stacked_bar_chart_for_course_specific_engagement,
    create_empty_chart_in_case_of_errors
)
from processors.overall_discourseData_processors import create_weekwise_engagement


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
    relevant_df = relevant_df[(relevant_df["acting_username"].str.lower()).isin(user_list)]  # filter based on user_list
    
    if not relevant_df.empty:
        chart = create_stacked_bar_chart_for_course_specific_engagement(relevant_df, course)  # create activity chart specific to user list
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

    # Finding the top-10 users
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


def generate_weekwise_chart(course_name, term):
    """Generate weekwise engagement chart for a specific course and term."""
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    user_actions_df = user_actions_dictionaries[term][course_name]["user_actions_df"]
    weekwise_engagement_chart = create_weekwise_engagement(user_actions_df)
    return weekwise_engagement_chart