from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from authlib.integrations.flask_client import OAuth
import os, json
import pandas as pd
from functools import lru_cache
from markupsafe import Markup

# Imports from other files
from user_summary_functions import get_user_summary, get_basic_metrics, get_top_categories, get_liked_by_users

from subject_wise_engagement.data_dicts import get_all_data_dicts
from subject_wise_engagement.global_functions_1 import get_current_trimester
from subject_wise_engagement.execute_query import execute_query_108

from visualizations.functions_to_get_charts import create_stacked_bar_chart_for_overall_engagement, create_stacked_bar_chart_for_course_specific_engagement, create_empty_chart_in_case_of_errors

# GLOBAL VARIABLES
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")  # secret key to secure cookies and session data.
oauth = OAuth(app) # OAuth is a way to safely let users login using Google without handling their passwords yourself

# DATA VARIABLES
user_actions_dictionaries = get_all_data_dicts()
id_username_mapping = execute_query_108(query_id=108)

google = oauth.register( # Then you told OAuth: Hey OAuth
    
    name='google', # register Google as a login provider, and here’s my
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

def find_latest_chart(dir_list):
    term_list = [k.split("_")[3] for k in dir_list]
    year_list = [k.split("_")[-1].split(".")[0] for k in dir_list]
    term_list.sort(), year_list.sort()
    latest_chart = f"most_active_users_{term_list[0]}_{year_list[-1]}.html"
    return latest_chart

@lru_cache(maxsize=None)
def generate_chart_for_overall_engagement(term):
    unnormalized_df = user_actions_dictionaries[term]["overall"]["unnormalized_scores"]
    unnormalized_df = unnormalized_df[unnormalized_df["user_id"]>0]
    top_10_users = pd.DataFrame(unnormalized_df.head(10))
    # id_username_mapping = pd.read_csv("data/id_username_mapping.csv")
    top_10_users = top_10_users.merge(id_username_mapping, on="user_id")
    chart = create_stacked_bar_chart_for_overall_engagement(top_10_users, term=term)
    return chart

@lru_cache(maxsize=None)
def get_users_engagement_chart(course, user_list, term="t1-2025"):
    user_list = [name.lower().strip() for name in user_list]
    relevant_df = user_actions_dictionaries[term][course]["unnormalized_scores"]
    relevant_df = relevant_df[(relevant_df["acting_username"].str.lower()).isin(user_list)] # filter based on user_list
    if not relevant_df.empty:
        chart = create_stacked_bar_chart_for_course_specific_engagement(relevant_df,course) # create activity chart specific to user list
        return chart
    else:
        return create_empty_chart_in_case_of_errors(message="None of the users from the list was found, please provide a new set of users.")

@lru_cache(maxsize=None)
def generate_chart_for_course_specific_engagement(term, subject):
    print("SUBJECT = ", subject, "TERM = ",term)
    # print(f"KEYS = {user_actions_dictionaries[term].keys()}")
    log_normalized_df = user_actions_dictionaries[term][subject]["log_normalized_scores"]
    if not log_normalized_df.empty:
        top_10 = log_normalized_df.head(10).acting_username.to_list()
        raw_metrics = user_actions_dictionaries[term][subject]["raw_metrics"]
        raw_metrics = raw_metrics[raw_metrics.acting_username.isin(top_10)]
        chart = create_stacked_bar_chart_for_course_specific_engagement(raw_metrics=raw_metrics, subject=subject)
    else:
        chart = create_empty_chart_in_case_of_errors(message = """Course was either not offered this term OR it had extremely less interactions on discourse""")
    
    return chart

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

@app.route('/get_chart')
def get_chart():
    chart = request.args.get('chart')
    print(f"Selected Chart INSIDE get_chart() = {chart}")
    if chart:
        # Generate the chart for the selected term
        chart_html = generate_chart_for_overall_engagement(chart).to_html()
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
    course_name_original = course_name
    try:
        course_name_original = course_name
        course_name = course_name.replace("-", "_").replace(":","_")
        chart = generate_chart_for_course_specific_engagement(term="t1-2025", subject=course_name)
        
        # Convert the chart to an HTML string
        chart_html = chart.to_html()

        return render_template(
            'course_specific_viz.html',
            course_name=course_name_original.title().replace("_"," "),
            latest_visualizations_html=Markup(chart_html)  # Mark it safe explicitly
        )
    except Exception as e:
        return render_template(
            'course_specific_viz.html',
            course_name=course_name_original.title().replace("_"," "),
            latest_visualizations_html=Markup(create_empty_chart_in_case_of_errors().to_html())
        )


@app.route("/user_details/<user_name>", methods=["GET"])
def get_user_details(user_name):
    summary_data = get_user_summary(user_name)
    basic_metrics, top_categories, most_liked_by = get_basic_metrics(summary_data), get_top_categories(summary_data), get_liked_by_users(summary_data)
    return jsonify({
        'basic_metrics': basic_metrics.to_dict(orient="records"),
        'top_categories': top_categories.to_dict(orient="records"),
        'most_liked_by': most_liked_by.to_dict(orient="records"),
        # "email": email
    })

@app.route("/<course_name>/get_specific_users_stat", methods=["POST"])
def specific_users_stat(course_name):
    # try:
        course_name = course_name.replace("-", "_").replace(":", "_").lower()
        user_list = request.form.get("user_list")
        if not user_list:
            return jsonify({"error": "No usernames provided."}), 400

        user_list = tuple(user_list.split(","))
        chart = get_users_engagement_chart(course_name, user_list)
        return chart.to_html()  # ← raw HTML string
    # except Exception as e:
    #     print(f"Error: {e}")
    #     return jsonify({"error": "Internal error occurred."}), 500


@app.route('/search_user')
def search_user():
    return render_template('user.html')



if __name__ == '__main__':
    app.run(host='0.0.0.0', 
            port=5000, 
            debug=True, 
            use_reloader=False
            )