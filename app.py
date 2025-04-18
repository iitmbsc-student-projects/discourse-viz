from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from authlib.integrations.flask_client import OAuth
import os
import yaml
from user_summary_functions import get_user_summary, get_basic_metrics, get_top_categories, get_liked_by_users, get_user_email


# with open("./key.yaml", "r") as file:
#     keys = yaml.safe_load(file)

# GLOBAL VARIABLES
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")  # Replace with your secret key
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id= os.environ.get("GOOGLE_AUTH_CLIENT_ID"),
    client_secret= os.environ.get("GOOGLE_AUTH_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
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

@app.route('/')
def index():
    # Fetch the list of overall discourse charts
    overall_discourse_charts_path = os.path.join(app.static_folder, 'visualizations', 'overall_discourse_charts')
    overall_discourse_charts = os.listdir(overall_discourse_charts_path)
    latest_chart = find_latest_chart(overall_discourse_charts)
    # print("LATEST_CHART = ", latest_chart)

    # Get the selected chart from the query parameters
    selected_chart = request.args.get('chart')

    return render_template('index.html', 
                           foundation_courses=foundation_courses,
                           diploma_programming_courses=diploma_programming_courses,
                           diploma_data_science_courses=diploma_data_science_courses,
                           degree_courses=degree_courses,
                           overall_discourse_charts=overall_discourse_charts,
                           selected_chart=selected_chart,
                           latest_chart=latest_chart)

@app.route('/get_chart')
def get_chart():
    chart = request.args.get('chart')
    if chart:
        chart_path = os.path.join(app.static_folder, 'visualizations', 'overall_discourse_charts', chart)
        # print(f"Requested chart path: {chart_path}")  # Debugging line
        chart_html = f"""
        <h2>Selected Chart: {chart.split('.')[0].replace('_', ' ')}</h2>
        <iframe src="{url_for('static', filename='visualizations/overall_discourse_charts/' + chart)}" 
                width="100%" height="600" style="border: none; border-radius: 8px;"></iframe>
        """
        return chart_html
    return "<h2>No chart selected</h2>"

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

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
        )

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
    # print(f"Recieved course name = {course_name}")
    course_name = course_name.replace("-", "_").replace(":","_")
    # print(f"NEW course name = {course_name}")

    # Get path to Altair-generated HTML visualizations
    latest_visualizations_html_path = url_for('static', filename=f'visualizations/course_specific_charts/t1_2025/{course_name}.html')

    # print(f"latest_visualizations_html_path === {latest_visualizations_html_path}")

    return render_template('course_specific_viz.html', course_name=course_name_original.title().replace("_"," "), latest_visualizations_html_path = latest_visualizations_html_path)

@app.route("/user_details/<user_name>", methods=["GET"])
def get_user_details(user_name):
    summary_data = get_user_summary(user_name)
    basic_metrics, top_categories, most_liked_by, email = get_basic_metrics(summary_data), get_top_categories(summary_data), get_liked_by_users(summary_data), get_user_email(user_name)
    return jsonify({
        'basic_metrics': basic_metrics.to_dict(orient="records"),
        'top_categories': top_categories.to_dict(orient="records"),
        'most_liked_by': most_liked_by.to_dict(orient="records"),
        "email": email
    })

@app.route('/search_user')
def search_user():
    return render_template('user.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)