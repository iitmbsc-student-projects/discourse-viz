from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    all_users_engagement_viz = os.path.join(app.static_folder, 'overall_engagement_charts')
    images = [f for f in os.listdir(all_users_engagement_viz) if f.endswith('.png')]

    foundation_courses = ["Programming in Python", "English II", "Course 3"]
    diploma_programming_courses = ["Database Management Systems", "Modern Application Development I", "Course 6"]
    diploma_data_science_courses = ["Machine Learning Foundations", "Course 8", "Course 9"]
    degree_courses = ["Course 10", "Course 11", "Course 12"]

    return render_template('index.html', images=images, 
                           foundation_courses=foundation_courses,
                           diploma_programming_courses=diploma_programming_courses,
                           diploma_data_science_courses=diploma_data_science_courses,
                           degree_courses=degree_courses)

@app.route("/<course_name>")
def course_page(course_name):
    course_name = course_name.replace("-", "_")
    # print(course_name)
    visualizations_image_path = os.path.join(app.static_folder, 'visualizations', f"most_active_users_{course_name}.png")
    # print(visualizations_image_path)
    return (render_template('course_specific_viz.html', course_name=course_name, images = [f"most_active_users_{course_name}.png"])) # Images is kept as a list because there can be multiple images for a course.

if __name__ == '__main__':
    app.run(debug=True)