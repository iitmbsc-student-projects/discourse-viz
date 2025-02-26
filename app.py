from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    visualizations = ["most_active_users_all_users.html"] # Kept as a list because there could be multiple visualizations for all_users data

    foundation_courses = ["Programming in Python", "English II", "Course 3"]
    diploma_programming_courses = ["Database Management Systems", "Modern Application Development I", "Course 6"]
    diploma_data_science_courses = ["Machine Learning Foundations", "Course 8", "Course 9"]
    degree_courses = ["Course 10", "Course 11", "Course 12"]

    return render_template('index.html', 
                           visualizations = visualizations, 
                           foundation_courses=foundation_courses,
                           diploma_programming_courses=diploma_programming_courses,
                           diploma_data_science_courses=diploma_data_science_courses,
                           degree_courses=degree_courses)

@app.route("/<course_name>")
def course_page(course_name):
    course_name = course_name.replace("-", "_")

    # Get path to Altair-generated HTML visualizations
    visualizations_html_path = os.path.join(app.static_folder, 'visualizations', f"most_active_users_{course_name}.html")

    return render_template('course_specific_viz.html', course_name=course_name, visualizations=[f"most_active_users_{course_name}.html"])


if __name__ == '__main__':
    app.run(debug=True)