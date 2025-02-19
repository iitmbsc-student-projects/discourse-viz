from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    visualizations_dir = os.path.join(app.static_folder, 'visualizations')
    images = [f for f in os.listdir(visualizations_dir) if f.endswith('.png')]    
    return render_template('index.html', images=images)

if __name__ == '__main__':
    app.run(debug=True)