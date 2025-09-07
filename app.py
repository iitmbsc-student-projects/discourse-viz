from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from authlib.integrations.flask_client import OAuth
import os, json, time, threading
import pandas as pd 
from functools import lru_cache # This is used to cache the results of the functions
from markupsafe import Markup # This is used to safely render HTML content
from apscheduler.schedulers.background import BackgroundScheduler # This is used to schedule the daily refresh of the data
from datetime import datetime, timedelta # This is used to get the current date and time

# Imports from other files
from auth import init_oauth, register_auth_routes
from config import Config
from constants import foundation_courses, diploma_programming_courses, diploma_data_science_courses, degree_courses
import data_loader
from utils import sanitize_filepath, get_current_trimester, get_previous_trimesters

from user_summary_functions import get_user_summary, get_basic_metrics, get_top_categories, get_liked_by_users

from data_processor import get_all_data_dicts

from global_functions_1 import create_weekwise_engagement, create_raw_metrics_dataframe, create_unnormalized_scores_dataframe, create_log_normalized_scores_dataframe, weights_dict_for_overall_engaagement, create_log_normalized_scores_dataframe_for_all_users, create_unnormalized_scores_dataframe_for_all_users

from execute_query import execute_query_108, execute_query_103, execute_query_102

from functions_to_get_charts import create_stacked_bar_chart_for_overall_engagement, create_stacked_bar_chart_for_course_specific_engagement, create_empty_chart_in_case_of_errors

# GLOBAL VARIABLES & FLAGS
app = Flask(__name__)
app.config.from_object(Config)
oauth, google = init_oauth(app)
register_auth_routes(app, google) # GOOGLE AUTH ROUTES


def get_top_respondents_from_useractions_df(course): # Put this function in processors.py file in new structure
    term = get_current_trimester()
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    df = (user_actions_dictionaries[term][course]["user_actions_df"]).copy(deep=True) # Make a copy to avoid modifying the original dataframe
    if df.empty:
        raise ValueError("The user actions dataframe is empty, cannot compute top respondents.")
    
    df['created_at'] = pd.to_datetime(df['created_at']) # Convert created_at to datetime for sorting

    # Step 1: Get all new topics
    new_topics = df[df['action_name'] == 'new_topic'][['target_topic_id', 'topic_title', 'created_at']]

    # Step 2: For each topic, find the first reply/response after the new_topic timestamp
    first_responders = []

    for _, row in new_topics.iterrows():
        topic_id = row['target_topic_id']
        topic_time = row['created_at']
        topic_title = row['topic_title']
        
        # Get replies/responses for this topic AFTER the topic creation time
        replies = df[(df['target_topic_id'] == topic_id) & 
                    (df['action_name'].isin(['reply', 'response'])) &
                    (df['created_at'] > topic_time)]
        
        if not replies.empty:
            first_reply = replies.sort_values('created_at').iloc[0]
            first_responders.append((topic_title, first_reply['acting_username'], first_reply['created_at']))

    # Convert to DataFrame
    first_responders_df = pd.DataFrame(first_responders, columns=['topic_title', 'first_responder', 'response_time'])

    # Count most frequent first responders
    most_freq_first_responders = first_responders_df['first_responder'].value_counts().head(10)
    most_freq_first_responders_list = list(most_freq_first_responders.items())
    return most_freq_first_responders_list

def get_trending_topics_from_useractions_df(course): # Put this function in processors.py file in new structure
    term = get_current_trimester()
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    df = (user_actions_dictionaries[term][course]["user_actions_df"]).copy() # Make a copy to avoid modifying the original dataframe
    if df.empty:
        raise ValueError("The user actions dataframe is empty, cannot compute trending topics.")
    
    # Convert created_at to datetime for sorting
    df['created_at'] = pd.to_datetime(df['created_at'], format='mixed')  # Handles UTC & IST

    # Define weights for actions
    weights = {
        'response': 0.5,
        'like': 0.35,
        'quote': 3,
    }

    # 1. Find topics created in the last 7 days
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    seven_days_ago_utc = pd.Timestamp(seven_days_ago, tz='UTC')  # Convert to UTC
    recent_topics = df[(df['action_name'] == 'new_topic') & (df['created_at'] >= seven_days_ago_utc)]
    recent_topic_ids = set(recent_topics['target_topic_id'])

    # 2. Filter actions for these topics (excluding 'new_topic')
    recent_actions = df[(df['target_topic_id'].isin(recent_topic_ids)) &
                        (df['action_name'].isin(weights.keys()))]

    # 3. Group by topic and count actions
    topic_action_counts = recent_actions.groupby(['target_topic_id', 'action_name']).size().unstack(fill_value=0)

    # Preserve original counts before applying weights
    counts_df = topic_action_counts.copy()

    # 4. Compute raw scores using weights
    for action, weight in weights.items():
        if action in topic_action_counts.columns:
            topic_action_counts[action] *= weight

    topic_action_counts['raw_score'] = topic_action_counts.sum(axis=1)

    # 5. Add topic creation time and title
    topic_info = recent_topics.set_index('target_topic_id')[['topic_title', 'created_at']]
    merged = topic_action_counts.merge(topic_info, left_index=True, right_index=True)

    # 6. Normalize by age (in hours)
    now_utc = pd.Timestamp(now, tz='UTC')
    merged['hours_since_creation'] = (now_utc - merged['created_at']).dt.total_seconds() / 3600
    merged['normalized_score'] = merged['raw_score'] / merged['hours_since_creation']

    # Merge counts for final output
    merged = merged.merge(counts_df, left_index=True, right_index=True, suffixes=('', '_count'))

    # 7. Sort and get top 10
    top_trending = merged.sort_values('normalized_score', ascending=False).head(10)

    # Build final output list: (topic_id, topic_url, topic_title, response_count, like_count, quote_count)
    top_trending_list = []
    for topic_id, row in top_trending.iterrows():
        url = f"https://discourse.onlinedegree.iitm.ac.in/t/{topic_id}"
        topic_title = row['topic_title']
        response_count = row.get('response', 0)
        like_count = row.get('like', 0)
        quote_count = row.get('quote', 0)
        top_trending_list.append((topic_id, url, topic_title, int(response_count), int(like_count), int(quote_count)))

    return top_trending_list


def generate_chart_for_overall_engagement(term):
    try:
        user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
        id_username_mapping = data_loader.get_id_username_mapping()
        unnormalized_df = user_actions_dictionaries[term]["overall"]["unnormalized_scores"]
        unnormalized_df = unnormalized_df[unnormalized_df["user_id"]>0]
        top_10_users = pd.DataFrame(unnormalized_df.head(10))
        top_10_users = top_10_users.merge(id_username_mapping, on="user_id")
        chart = create_stacked_bar_chart_for_overall_engagement(top_10_users, term=term)
        return chart
    except:
        chart = create_empty_chart_in_case_of_errors(message= "The chart may not have been loaded properly, please wait for some time and then refresh. Contact support if issue persists.")
        return chart

def get_users_engagement_chart(course, user_list, term="t1-2025"):
    """
    Returns the course-specific chart of a specific set of users; uses unnormalised dataframe
    """
    user_list = [name.lower().strip() for name in user_list]
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    relevant_df = user_actions_dictionaries[term][course]["unnormalized_scores"]
    relevant_df = relevant_df[(relevant_df["acting_username"].str.lower()).isin(user_list)] # filter based on user_list
    if not relevant_df.empty:
        chart = create_stacked_bar_chart_for_course_specific_engagement(relevant_df,course) # create activity chart specific to user list
        return chart
    else:
        return create_empty_chart_in_case_of_errors(message="None of the users from the list was found, please provide a new set of users.")

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
        highest_activity_chart = create_stacked_bar_chart_for_course_specific_engagement(raw_metrics=raw_metrics, subject=subject)
    else:
        highest_activity_chart = create_empty_chart_in_case_of_errors(message = """Course was either not offered this term OR it had extremely less interactions on discourse""")
    
    return highest_activity_chart

@app.route('/')
def index():
    latest_term = get_current_trimester()
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    return render_template('index.html', 
                           foundation_courses=foundation_courses,
                           diploma_programming_courses=diploma_programming_courses,
                           diploma_data_science_courses=diploma_data_science_courses,
                           degree_courses=degree_courses,
                           overall_discourse_charts=list(user_actions_dictionaries.keys()), # LIST of terms (current and past)
                           latest_chart=latest_term)

@app.route('/loading-status')
def loading_status():
    user_actions_loaded = data_loader.get_user_actions_loaded()
    return {"loaded": user_actions_loaded}

@app.route('/get_chart') # Used to get the Overall Discourse Charts on the home page
def get_overall_discourse_chart():
    user_actions_loaded = data_loader.get_user_actions_loaded()
    if not user_actions_loaded:
        return "<h3 style='color:violet'>Data is still loading. Once the background data fetching is completed, the chart will automatically be rendered.<br>Kindly wait for a few minutes!</h3>"
    term = request.args.get('chart')
    if term:
        # Generate the chart for the selected term
        chart_html = generate_chart_for_overall_engagement(term).to_html()
        return chart_html
    else:
        return "<h2>No chart selected</h2>"

@app.route("/<course_name>")
def course_page(course_name):
    course_name_original = course_name
    try:
        course_name = course_name.replace("-", "_").replace(":","_")
        return render_template(
            'course_specific_viz.html',
            term_list_for_dropdown = get_previous_trimesters(get_current_trimester())[:2], # List of terms for dropdown, like ["t2-2025","t1-2025","t3-2024"] # CHANGED FOR TESTING
            course_name=course_name_original.title().replace("_"," "),
            course_name_escaped=course_name  # Pass the escaped course name to the template
        )
    except Exception as e:
        print(f"Error in course_page for course = {course_name}: {e}")
        return render_template(
            'course_specific_viz.html',
            course_name=course_name_original.title().replace("_"," "),
            course_name_escaped=course_name,
            error=str(e)
        )

# New endpoint that returns only the top users chart
@app.route("/<course_name>/top_users_chart/<term>")
def top_users_chart(course_name, term):
    try:
        course_name = course_name.replace("-", "_").replace(":","_").lower()
        top_10_users_chart = get_top_10_users_chart(term=term, subject=course_name)
        return top_10_users_chart.to_html()
    except Exception as e:
        print(f"Error in top_users_chart for course = {course_name}: {e}")
        empty_chart = create_empty_chart_in_case_of_errors(message="Could not load top users chart; the course might not have been offered")
        return empty_chart.to_html()

# New endpoint that returns only the weekwise engagement chart
@app.route("/<course_name>/weekwise_chart/<term>")
def weekwise_chart(course_name, term):
    try:
        course_name = course_name.replace("-", "_").replace(":","_").lower()
        user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
        user_actions_df = user_actions_dictionaries[term][course_name]["user_actions_df"]
        weekwise_engagement_chart = create_weekwise_engagement(user_actions_df)
        return weekwise_engagement_chart.to_html()
    except Exception as e:
        print(f"Error in weekwise_chart for course = {course_name}: {e}")
        empty_chart = create_empty_chart_in_case_of_errors(message="Could not load weekly engagement chart; the course might not have been offered")
        return empty_chart.to_html()

@app.route("/get_most_frequent_first_responders/<course_name>", methods = ["GET"])
def most_frequent_first_responders(course_name):
    """ This function fetches the most frequent first responders for a given course."""
    try:
        current_term = get_current_trimester() # For example, "t1-2025"
        course_name = course_name.replace("-", "_").replace(":","_").lower()
        most_freq_first_responders_list = get_top_respondents_from_useractions_df(course_name)
    except Exception as e:
        most_freq_first_responders_list = []
        print(f"Encountered an error while finding most_frequent_first_responders: {e} ")
    return render_template("partials/first_responders_table.html", most_freq_first_responders=most_freq_first_responders_list, current_term=current_term)

@app.route("/user_details/<user_name>", methods=["GET"]) # This route is invoked when user clicks on the "search" button on the "search_user" page
def get_user_details(user_name):
    """ This function fetches the user details for a given username."""
    summary_data = get_user_summary(user_name)
    basic_metrics, top_categories, most_liked_by = get_basic_metrics(summary_data), get_top_categories(summary_data), get_liked_by_users(summary_data)
    return jsonify({
        'basic_metrics': basic_metrics.to_dict(orient="records"),
        'top_categories': top_categories.to_dict(orient="records"),
        'most_liked_by': most_liked_by.to_dict(orient="records"),
        # "email": email
    })

@app.route("/<course_name>/get_specific_users_stat", methods=["POST"])
def specific_users_stat(course_name): # Returns a chart showing activity of a set of users
    try: # We will use try-except block during final deployment
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        user_list = request.form.get("user_list")
        selected_term = request.form.get("selected_term")
        if not user_list:
            return jsonify({"error": "No usernames provided."}), 400

        user_list = tuple(user_list.split(","))
        chart = get_users_engagement_chart(course_name, user_list, term = selected_term)
        return chart.to_html()  # ← raw HTML string
    except Exception as e:
        print(f"Error: {e} in specific_users_stat function for the route /{course_name}/get_specific_users_stat")
        return jsonify({"error": "Internal error occurred."}), 500


@app.route('/search_user') # Invoked when user clicks on "Search User" button
def search_user():
    return render_template('user.html')

@app.route("/most_trending_topics/<course_name>", methods = ["GET"])
def most_trending_topics(course_name):
    """
    This function fetches the most trending topics for a given course.
    It uses the course name to find the corresponding slug and category_id from df_map_category_to_id.
    Then it fetches the recent topics using the fetch_recent_topics function and computes the trending scores using the compute_trending_scores function.
    Finally, it renders the trending topics table using the trending_scores.
    """
    try:
        trending_scores = get_trending_topics_from_useractions_df(course_name)
        return render_template("partials/trending_topics_table.html", trending_scores=trending_scores)
    except Exception as e:
        return render_template("partials/trending_topics_table.html", trending_scores=[])

    

if __name__ == '__main__':
    # Initial load
    # Use data_loader functions instead of duplicating the logic
    df_map_category_to_id, id_username_mapping, user_actions_dictionaries = data_loader.init_minimal_data() # Blocking: ~2 mins
    threading.Thread(target=data_loader.background_load_user_actions, daemon=True).start()

    # Schedule daily refresh
    scheduler = BackgroundScheduler()
    scheduler.add_job(data_loader.refresh_all_data, 'cron', hour=1, minute=0) # refresh data every day at 1am
    scheduler.start()

    app.run(host='0.0.0.0', 
            port=5000, 
            debug=True, 
            use_reloader=False # Prevents the scheduler from starting twice when debug mode is enabled.
            )