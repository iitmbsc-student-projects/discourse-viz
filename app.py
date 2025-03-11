from flask import Flask, render_template, redirect, url_for, session, request, flash
from authlib.integrations.flask_client import OAuth
import os, yaml, time

with open("./key.yaml", "r") as file:
    keys = yaml.safe_load(file)


app = Flask(__name__)
app.secret_key = keys["secret_key"]  # Replace with your secret key
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id= keys["google_auth_client_id"],
    client_secret= keys["google_auth_client_secret"],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/')
def index():
    visualizations = ["most_active_users_all_users.html"]  # Kept as a list because there could be multiple visualizations for all_users data

    foundation_courses = ["Programming in Python", "English II", "Course 3"]
    diploma_programming_courses = ["Database Management Systems", "Modern Application Development I", "Course 6"]
    diploma_data_science_courses = ["Machine Learning Foundations", "Course 8", "Course 9"]
    degree_courses = ["Course 10", "Course 11", "Course 12"]

    return render_template('index.html', 
                           visualizations=visualizations, 
                           foundation_courses=foundation_courses,
                           diploma_programming_courses=diploma_programming_courses,
                           diploma_data_science_courses=diploma_data_science_courses,
                           degree_courses=degree_courses)

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
    course_name = course_name.replace("-", "_")

    # Get path to Altair-generated HTML visualizations
    visualizations_html_path = os.path.join(app.static_folder, 'visualizations', f"most_active_users_{course_name}.html")

    return render_template('course_specific_viz.html', course_name=course_name, visualizations=[f"most_active_users_{course_name}.html"])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)