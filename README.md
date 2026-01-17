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
    ./venv/Scripts/activate

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
- `user_summary/`:user summary logic.

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



## Visualizations used
- For each course, we have identified **top-10 active users** based on the z-scores of the **log-normalized data**. This will be rendered on the course-specific page. The visualization used is a stacked bar chart showing the individual metrics of the active users in a single chart.
- For the home page, we have identified **top-10 active users** based on the "unnormalized" z-scores of the overall discourse data.



## Architecture Overview

### Data Flow
- **Initial Load** (~2 min): Loads course list and user mappings, creates empty data structure
- **Background Load** (~30 min): Fetches full trimester data from Discourse API in a separate thread
- **Daily Refresh** (3:30 AM): Incremental data update to keep analytics fresh

### Key Components
- **Discourse API**: Source of user activity data (queries 102, 103, 107, 108)
- **user_actions_dictionaries**: Global in-memory cache storing 3 trimesters of data
- **Scoring System**: Raw metrics → Unnormalized scores → Log-normalized scores
- **Authentication**: Google OAuth 2.0 (IIT Madras email domain required)

## Configuration

### Environment Variables
Create a `.env` file or set these in your environment. Using a `.env` file with a library like `python-dotenv` is the recommended approach for managing secrets and configuration during development. If you are setting these vars in `.env` file, you have to use dotenv to load these vars in your code. Kindly use copilot for the code of the same.

```bash
# Required for API access
DISCOURSE_API_KEY=your_api_key_here
GOOGLE_AUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_AUTH_CLIENT_SECRET=your_client_secret
SECRET_KEY=random_long_secret_string_for_sessions
```
Getting Discourse API Key
- (Ask either the developer, or the IITM support team)

Getting Google OAuth Credentials
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create OAuth 2.0 Client ID (Web application)
- Add authorized redirect URI: http://localhost:5000/auth/callback
- Copy Client ID and Secret to .env
- Ask CoPilot for help on this specific thing; contact developer if more info is needed.

## How the app works

### Data Processing Pipeline
1. **Query Discourse API** → Get user actions (likes, posts, replies, etc.). All data is stored in `user_actions_dictionaries` variable
2. **Create Raw Metrics** → Count actions per user
3. **Calculate Scores** → Apply weights to metrics
4. **Log Normalization** → Reduce impact of outliers
5. **Display Charts** → Show top users in stacked bar charts

### Visual Structure of `user_actions_dictionaries` after data loading
```python
user_actions_dictionaries = {
    "t2-2025": {                           # Current trimester
        "MLF": {
            "user_actions_df": <DataFrame>,
            "raw_metrics": <DataFrame>,
            "unnormalized_scores": <DataFrame>,
            "log_normalized_scores": <DataFrame>
        },
        "PDSA": { ... },
        "English1": { ... },
        "OVERALL_DISCOURSE": {            # IMP: Platform-wide data
            "raw_metrics": <DataFrame>,
            "unnormalized_scores": <DataFrame>,
            "log_normalized_scores": <DataFrame>
        }
    },
    "t1-2025": { ... },                    # Previous trimester
    "t3-2024": { ... }                     # 2 trimesters back
}
```

### You can download the [pickle file](https://drive.google.com/file/d/15WPcxBvEE1s-lZwxlWOOhR2qLSoc9pmz/view?usp=sharing) and explore it using python.

### Scoring Weights
- **Course-specific**: Solving topics (3.0) > Receiving likes (0.8) > Replying (0.7) > Creating topics (0.5) > Giving likes (0.3)
- **Overall engagement**: Solutions (3.0) > Receiving likes (0.8) > Posts created (0.7) > Topics created (0.4) > Giving likes (0.4) > Days visited (0.3)

### User Authentication
- Uses Google OAuth 2.0
- Only allows emails ending with `@study.iitm.ac.in`
- Session data stored in encrypted cookies

Here’s a **README-friendly version** that’s clean, scannable, and appropriate for a GitHub project. It balances structure with brief explanations so new contributors can quickly understand the codebase.

---

## Project Structure

This project follows a modular Flask architecture, separating configuration, core logic, data processing, routing, and presentation layers for clarity and maintainability.

```text
discourse-viz/
├── app.py
│   Main Flask application entry point.
│   Initializes the app, registers blueprints, and sets up scheduled tasks.
│
├── application/
│   ├── config.py
│   │   Flask configuration (environment variables, app settings).
│   └── constants.py
│       Shared constants such as API keys, course lists, and scoring weights.
│
├── core/
│   ├── auth.py
│   │   Google OAuth authentication logic.
│   ├── data_loader.py
│   │   Centralized data loading and caching.
│   ├── data_processor.py
│   │   Core data aggregation and transformation logic.
│   ├── execute_query.py
│   │   Discourse API query execution (query IDs: 102, 103, 107, 108).
│   └── utils.py
│       General helper utilities (dates, trimesters, formatting, etc.).
│
├── processors/
│   ├── course_data_processors.py
│   │   Per-course engagement and metric calculations.
│   ├── overall_discourseData_processors.py
│   │   Platform-wide Discourse analytics and summaries.
│   ├── chart_processors.py
│   │   Data preparation for visualizations.
│   └── functions_to_get_charts.py
│       Altair chart generation functions.
│
├── routes/
│   ├── __init__.py
│   │   Flask blueprint registration.
│   ├── api.py
│   │   General routes (home, about, health checks).
│   ├── courses.py
│   │   Course-specific views and APIs.
│   ├── charts.py
│   │   Routes for overall engagement and analytics charts.
│   └── users.py
│       User search and profile pages.
│
├── user_summary/
│   └── user_summary_functions.py
│       Individual user profile aggregation (direct Discourse API calls).
│
├── templates/
│   Jinja2 HTML templates.
│
├── static/
│   Static assets (CSS, JavaScript, images).
│
└── requirements.txt
    Python dependencies for the project.
```

---



## Troubleshooting

### Data Not Loading
- Check if `DISCOURSE_API_KEY` is set correctly
- Check logs in `logs/` directory
- Verify network connectivity to Discourse instance
- Check if user account has API access permissions

### Google Login Not Working
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Check redirect URI matches exactly in Google Cloud Console
- Ensure using `@study.iitm.ac.in` email

### Scheduler Not Running
- Check `use_reloader=False` in `app.py`
- Check logs for APScheduler errors
- In production, use external cron jobs instead

### Empty Charts
- Wait for background data load to complete (~30 min after startup)
- Save the user_actions_dictionaries as a pickle file (inside the load_user_actions_dictionaries() function), and then analyse the contents carefully for debugging.
- Check if courses have any user activity in selected trimester

## Development Notes

### Adding New Courses
1. Update course lists in `application/constants.py`. For example, if there is a new course, say "English 3" in the Degree level, you can simply add that course in the list `degree_level_courses` inside the file `constants.py`. The name of the course that you have added MUST MATCH the name in the list of courses returned by query 107. 
2. Commit the changes, they will be reflected if the deployment is successfull

### Deleting/Removing Courses

There are 2 ways to remove a course from being shown in the app

1. Suppose you want to remove the course "English II" from the analysis. Get the "category_id" for that course. You will find it in the dataframe returned by query 107. The "category_id" for "English II" is 22. So, add the integer 22 in the list `irrelevant_categories` in the function `load_df_map_category_to_id` inside the file `core/data_loader.py`. You also MUST have to remove 'English II' from the courses lists inside the `constants.py` file, else the course will still be visible on the frontend. On the next deployment, the data for "English II" will not be fetched.

2. We can simply remove 'English II' from the courses lists inside the `constants.py` file. This will simply remove the course from the frontend. The data for 'English II' will still be fetched. So, it's not a fool-proof way to remove a course from our analysis. The data for 'English II' will still be fetched in the backend.

### ERROR: 429 Client Error: Too Many Requests

If you are getting this error frequently, then increase `time.sleep(1.2)` --> `time.sleep(1.5)` and push the changes to remote.

### Modifying Scoring Weights
1. Update `weights_dict_for_course_specific_engagement` or `weights_dict_for_overall_engagement` in `constants.py`
2. Data will be recalculated on next deployment.

### Running Without Scheduler
For testing, comment out scheduler in `app.py`:
```python
# scheduler = BackgroundScheduler()
# scheduler.add_job(...)
# scheduler.start()
```

### Visit the [doc](https://docs.google.com/document/d/1udqmxOAxc_kR9tSkdpSa_dmfdd66MDINooI4d754WAk/edit?usp=sharing) where I have explained each major part of the code/pipeline

# Contact

For any questions or inputs, please contact Shubham Gattani (21f3002082@ds.study.iitm.ac.in).