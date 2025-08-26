from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from authlib.integrations.flask_client import OAuth
import os, json, time
import pandas as pd 
from functools import lru_cache # This is used to cache the results of the functions
from markupsafe import Markup # This is used to safely render HTML content
from apscheduler.schedulers.background import BackgroundScheduler # This is used to schedule the daily refresh of the data
from datetime import datetime, timedelta # This is used to get the current date and time

# Imports from other files
from user_summary_functions import get_user_summary, get_basic_metrics, get_top_categories, get_liked_by_users

from subject_wise_engagement.data_dicts import get_all_data_dicts

from subject_wise_engagement.global_functions_1 import get_current_trimester, create_weekwise_engagement, get_previous_trimesters, sanitize_filepath, create_raw_metrics_dataframe, create_unnormalized_scores_dataframe, create_log_normalized_scores_dataframe, weights_dict_for_overall_engaagement, create_log_normalized_scores_dataframe_for_all_users, create_unnormalized_scores_dataframe_for_all_users

from subject_wise_engagement.execute_query import execute_query_108, execute_query_103, execute_query_102

from subject_wise_engagement.fetch_category_IDs_107 import df_map_category_to_id

from visualizations.functions_to_get_charts import create_stacked_bar_chart_for_overall_engagement, create_stacked_bar_chart_for_course_specific_engagement, create_empty_chart_in_case_of_errors

# GLOBAL VARIABLES
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")  # secret key to secure cookies and session data.
oauth = OAuth(app) # OAuth is a way to safely let users login using Google without handling their passwords yourself



# DATA LOADER FUNCTIONS
def load_user_actions_dictionaries():
    from subject_wise_engagement.data_dicts import get_all_data_dicts
    return get_all_data_dicts()

def load_df_map_category_to_id():
    from subject_wise_engagement.fetch_category_IDs_107 import df_map_category_to_id
    return df_map_category_to_id

def load_id_username_mapping():
    from subject_wise_engagement.execute_query import execute_query_108
    # df = pd.read_csv("TRASH/data/id_username_mapping.csv") # REMOVE IN FINAL DEPLOYMENT
    df = execute_query_108(query_id=108, query_params=None) # UNCOMMENT IN FINAL DEPLOYMENT
    return df

# DATA VARIABLES
def get_all_data():
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping
    user_actions_dictionaries = load_user_actions_dictionaries()
    df_map_category_to_id = load_df_map_category_to_id()
    id_username_mapping = load_id_username_mapping()

def refresh_all_data(): # LATER, MOVE THIS FUNCTION TO DATA_DICTS.PY FILE
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping, last_refresh_date
    today = datetime.now().strftime("%d-%m-%Y")
    trimester_corresponding_to_today = get_current_trimester()
    trimester_data_to_be_removed = get_previous_trimesters(trimester_corresponding_to_today)[2] # For example, if today's trimester = "t2-2025", then DELETE any data corresponding to "t3-2024"    
    user_actions_dictionaries.pop(trimester_data_to_be_removed, None) # Remove the data, without raising eny errors
    print("User actions dictionaries keys: ", user_actions_dictionaries.keys())

    # Creating new data for each course
    for row in df_map_category_to_id.itertuples():
        category_id = row.category_id
        category_name = sanitize_filepath(row.name).lower() # Removes characters like :," " etc and replaces them with "_"
        if category_name not in user_actions_dictionaries[trimester_corresponding_to_today]:
            print(f"Inside refresh function for date = {today}\n{category_name} not found in user_actions_dictionaries for trimester {trimester_corresponding_to_today}")
            continue
        query_params_for_103 = {"category_id": str(category_id), "start_date": last_refresh_date, "end_date": today}

        latest_user_actions_df = execute_query_103(103, query_params=query_params_for_103) # This is the data between last_refresh_date and today
        print(f"Inside refresh function for date = {today}\nLatest user actions dataframe for {category_name} has {len(latest_user_actions_df)} rows")
        if not latest_user_actions_df.empty: # Modify existing data iff there is some change since last update

            # Now append this latest user_actions_df to the existing user_actions_df, and DROP the duplicate rows
            existing_user_actions_df = user_actions_dictionaries[trimester_corresponding_to_today][category_name]["user_actions_df"]
            new_user_actions_df = pd.concat([existing_user_actions_df, latest_user_actions_df]).drop_duplicates()
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["user_actions_df"] = new_user_actions_df

            # Now calculate the scores dataframe using new_user_actions_df
            new_raw_metrics_dataframe = create_raw_metrics_dataframe(new_user_actions_df)
            new_unnormalized_scores_df = create_unnormalized_scores_dataframe(new_raw_metrics_dataframe)
            new_log_normalized_scores_df = create_log_normalized_scores_dataframe(new_raw_metrics_dataframe)

            # Now assign the newly created dataframes to the original user_actions_dictionaries
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["raw_metrics"] = new_raw_metrics_dataframe
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["unnormalized_scores"] = new_unnormalized_scores_df
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["log_normalized_scores"] = new_log_normalized_scores_df
            
    # Updating data for overall engagement
    query_params_for_102 = {"start_date": last_refresh_date, "end_date": today}
    latest_raw_metrics_for_overall_engagement = execute_query_102(102, query_params = query_params_for_102)
    existing_raw_metrics_for_overall_engagement = user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["raw_metrics"]

    # Concatenate the latest raw metrics with the existing raw metrics, and drop duplicates
    new_raw_metrics_for_overall_engagement = pd.concat([latest_raw_metrics_for_overall_engagement, existing_raw_metrics_for_overall_engagement]).drop_duplicates()
    new_raw_metrics_for_overall_engagement = new_raw_metrics_for_overall_engagement.groupby("user_id", as_index=False).sum() # Group by user_id and sum all other metrics for each user

    new_raw_metrics_for_overall_engagement = new_raw_metrics_for_overall_engagement[["user_id"] + list(weights_dict_for_overall_engaagement.keys())]


    new_unnormalized_scores_dataframe_all_users, new_log_normalized_scores_dataframe_all_users = create_unnormalized_scores_dataframe_for_all_users(new_raw_metrics_for_overall_engagement), create_log_normalized_scores_dataframe_for_all_users(new_raw_metrics_for_overall_engagement)

    # Final assignment for all_users_engagement
    user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["raw_metrics"] = new_raw_metrics_for_overall_engagement
    user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["unnormalized_scores"] = new_unnormalized_scores_dataframe_all_users
    user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["log_normalized_scores"] = new_log_normalized_scores_dataframe_all_users

    last_refresh_date = today # Update the last refresh date to today
    print(f"Data refreshed successfully for {trimester_corresponding_to_today} trimester. Last refresh date is now set to {last_refresh_date}.")



google = oauth.register( # Then you told OAuth: Hey OAuth
    
    name='google', # register Google as a login provider, and here’s my...
    client_id= os.environ.get("GOOGLE_AUTH_CLIENT_ID"), # client_id
    client_secret= os.environ.get("GOOGLE_AUTH_CLIENT_SECRET"), # a secret password only your app and Google know
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration', # Google OpenID configuration URL (this tells your app where to send users to login)
    client_kwargs={'scope': 'openid email profile'} # meaning what user info you want to access.
)

foundation_courses = ['Mathematics for Data Science I','Statistics for Data Science I','Computational Thinking','English I','English II','Mathematics for Data Science II','Statistics for Data Science II','Programming in Python']
diploma_programming_courses = ['Programming, Data Structures and Algorithms','Database Management Systems','Modern Application Development I','System Commands','Modern Application Development II','Programming Concepts using Java']
diploma_data_science_courses = ['Machine Learning Foundations','Business Data Management','Machine Learning Techniques','Machine Learning Practice','Tools in Data Science','Business Analytics']
degree_courses = ['Deep Learning','AI: Search Methods for Problem Solving','Software Testing','Software Engineering','Strategies for Professional Growth','Industry 4.0','Design Thinking for Data Driven App Development','Speech Technology','Privacy & Security in Online Social Media','Algorithmic Thinking in Bioinformatics','Data Visualization Design','Linear Statistical Models','Market Research','Introduction to Big Data','Financial Forensics','Big Data and Biological Networks','Advanced Algorithms','Special topics in ML (Reinforcement Learning)','Statistical Computing','Programming in C','Mathematical Thinking','Computer System Design','Operating Systems','Deep Learning for Computer Vision','Large Language Models','Managerial Economics','Game Theory and Strategy','Corporate Finance','Deep Learning Practice','Introduction to Natural Language Processing']

degree_courses.sort()
diploma_data_science_courses.sort()
diploma_programming_courses.sort()
foundation_courses.sort()

def get_top_respondents_from_useractions_df(course): # Put this function in processors.py file in new structure
    term = get_current_trimester()
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

@lru_cache(maxsize=256)
def generate_chart_for_overall_engagement(term):
    try:
        unnormalized_df = user_actions_dictionaries[term]["overall"]["unnormalized_scores"]
        unnormalized_df = unnormalized_df[unnormalized_df["user_id"]>0]
        top_10_users = pd.DataFrame(unnormalized_df.head(10))
        # id_username_mapping = pd.read_csv("data/id_username_mapping.csv")
        top_10_users = top_10_users.merge(id_username_mapping, on="user_id")
        chart = create_stacked_bar_chart_for_overall_engagement(top_10_users, term=term)
        return chart
    except:
        chart = create_empty_chart_in_case_of_errors(message= "The chart may not have been loaded properly, please wait for some time and then refresh. Contact support if issue persists.")
        return chart

@lru_cache(maxsize=256)
def get_users_engagement_chart(course, user_list, term="t1-2025"):
    """
    Returns the course-specific chart of a specific set of users; uses unnormalised dataframe
    """
    user_list = [name.lower().strip() for name in user_list]
    relevant_df = user_actions_dictionaries[term][course]["unnormalized_scores"]
    relevant_df = relevant_df[(relevant_df["acting_username"].str.lower()).isin(user_list)] # filter based on user_list
    if not relevant_df.empty:
        chart = create_stacked_bar_chart_for_course_specific_engagement(relevant_df,course) # create activity chart specific to user list
        return chart
    else:
        return create_empty_chart_in_case_of_errors(message="None of the users from the list was found, please provide a new set of users.")

@lru_cache(maxsize=256)
def get_top_10_users_chart(term, subject):
    """
    Returns the course & term specific chart of top-10 most active users; uses log-normalised dataframe
    """
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
    return render_template('index.html', 
                           foundation_courses=foundation_courses,
                           diploma_programming_courses=diploma_programming_courses,
                           diploma_data_science_courses=diploma_data_science_courses,
                           degree_courses=degree_courses,
                           overall_discourse_charts=list(user_actions_dictionaries.keys()), # LIST of terms (current and past)
                           latest_chart=latest_term)

@app.route('/get_chart') # Used to get the Overall Discourse Charts on the home page
def get_overall_discourse_chart():
    term = request.args.get('chart')
    if term:
        # Generate the chart for the selected term
        chart_html = generate_chart_for_overall_engagement(term).to_html()
        return chart_html
    else:
        return "<h2>No chart selected</h2>"

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri) #User clicks Login → /login → Google login page → /auth/callback

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('google_token', None)
    return redirect(url_for('index'))

@app.route('/auth/callback') 
def authorized():
    token = google.authorize_access_token()
    if token is None:
        return 'Access denied: reason={} error={}'.format(
            request.args.get('error_reason'),
            request.args.get('error_description')
        ) # If token is missing (maybe user said "No" or an error happened),

    session['google_token'] = token
    user_info = google.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
    session['user'] = user_info
    email = user_info.get('email')

    # Check if the email ends with "study.iitm.ac.in"
    if not email.endswith('study.iitm.ac.in'):
        flash('Access denied: unauthorized email domain. Please login again with a valid email address.')
        session.pop('user', None)  # Clear the user session
        session.pop('google_token', None)  # Clear the token session
        return redirect(url_for('index'))

    session['user'] = user_info
    return redirect(url_for('index'))

@app.route("/<course_name>")
def course_page(course_name):
    current_term = get_current_trimester()
    previous_term = get_previous_trimesters(current_term)[1] # Get the previous term, for example, if latest_term = "t2-2025", then previous_term = "t1-2025"
    course_name_original = course_name
    try:
        course_name = course_name.replace("-", "_").replace(":","_")
        return render_template(
            'course_specific_viz.html',
            term_list_for_dropdown = [current_term, previous_term],
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
    get_all_data()

    # Schedule daily refresh
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_all_data, 'cron', hour=1, minute=0) # refresh data every day at 1am
    scheduler.start()

    app.run(host='0.0.0.0', 
            port=5000, 
            debug=True, 
            use_reloader=False # Prevents the scheduler from starting twice when debug mode is enabled.
            )