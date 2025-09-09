# Discourse Visualization

This project visualizes user engagement metrics for various courses. It is built using Flask and displays visualizations and course information on a web interface.

## Features

- Display visualizations of user engagement metrics.
- List courses for different levels: Foundation, Diploma in Programming, Diploma in Data Science, and Degree Level.

## Prerequisites

- Python 3.10 or above
- Virtual environment (highly recommended)

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/iitmbsc-student-projects/discourse-viz.git
    cd discourse-viz

    ## To open the repository directly in the VSCode, use the following command:
    code .
    ```

2. Create and activate a virtual environment:

    ```sh
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

4. Run the Flask application:

    ```sh
    python app.py
    ```

5. Open your web browser and go to `http://127.0.0.1:5000` to view the application.

## Project Structure

- `app.py`: The main Flask application file.
- `application/`: App configuration and constants.
- `core/`: Core logic for authentication, data loading, utilities, and query execution.
- `processors/`: Data processing and chart generation functions.
- `routes/`: All Flask route blueprints (API, charts, courses, users), except the auth routes which are in the `core/auth.py`.
- `templates/`: HTML templates for rendering pages and partials.
- `static/`: Static files like CSS and images.
- `requirements.txt`: List of required Python packages.
-`user_summary/`:user summary logic.

## How to Fork This Repository

Follow these steps to fork and set up this repository on your local machine:

1. **Fork the Repository**  
   - Click the **Fork** button in the top-right corner of this repo (on GitHub webUI). This creates a copy under your GitHub account.

2. **Clone Your Fork**  
   Open a terminal and run:  
   ```sh
   git clone https://github.com/YOUR-USERNAME/DISCOURSE_ANALYSIS_ICSR.git
   cd DISCOURSE_ANALYSIS_ICSR
   ```

4. **Make Your Changes**  
   - Create a new branch:  
     ```sh
     git checkout -b feature-branch
     ```
   - Make your edits, then commit:  
     ```sh
     git add .
     git commit -m "Your meaningful commit message"
     ```

5. **Push and Open a Pull Request**  
   ```sh
   git push origin feature-branch
   ```
   - Go to your fork on GitHub and click **"Contribute"** and then click on **"Open Pull Request"** to propose your changes.



# Visualizations used
- For each course, we have identified **top-10 active users** based on the z-scores of the **log-normalized data**. This will be rendered on the course-specific page. The visualization used is a stacked bar chart showing the individual metrics of the active users in a single chart.
- For the home page, we have identified **top-10 active users** based on the "unnormalized" z-scores of the overall discourse data.



# Contact

For any questions or inputs, please contact Shubham Gattani (21f3002082@ds.study.iitm.ac.in).
