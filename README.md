# Discourse Visualization

This project visualizes user engagement metrics for various courses. It is built using Flask and displays visualizations and course information on a web interface.

## Features

- Display visualizations of user engagement metrics.
- List courses for different levels: Foundation, Diploma in Programming, Diploma in Data Science, and Degree Level.

## Prerequisites

- Python 3.x
- Virtual environment (optional but recommended)

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/yourusername/discourse-viz.git
    cd discourse-viz
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

- app.py: The main Flask application file.
- templates: Directory containing HTML templates.
- static: Directory containing static files like CSS and images.
- requirements.txt: List of required Python packages.

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

# High level overview of the data-processing

- Query 102 is used to extract the information of all users "across all categories".
- Query 103 is used to extract the information of all users "across a specific category (say MLP)"
- For the data obtained using Query 103, it is converted into a pivot table in the format user_names x metrics. The pivot table is then converted into a dataframe (say df_1)
- The data obtained from Query 102 is already into proper format (say df_2)
- NOTE: The columns in both these dataframes are NOT the same. For example, "cheers","days_visited","posts_read" are in df_2 but not in df_1.
- To get the initial score of each user, we multiply each metrics with the corresponding weightage, and then sum them up.
- We then standardize the scores of all the users (using the mean and standard deviation). The z_score obtained from this is the "unnormalized" score of the user (because we haven't modified the individual feature_scores)
- We also apply log-normalization on the individual feature scores, and then sum them up to get the "initial_score", and finally standardize it to get the z_score. NOTE that we have applied log-normalization on the individual feature scores, and then summed them up, rather than first applying log-normalization on feature itself and them multiplying it with it's respective weight. Also note that we have used natural-log for the log-normalization.
- So we finally have two types of scores for each user: the "unnormalized" score and the "log-normalized" score.

# Visualizations used
- For each course, we have identified **top-5 active users** based on the z-scores of the **log-normalized data**. This will be rendered on the course-specific page. The visualization used is a stacked bar chart showing the individual metrics of the active users in a single chart.
- For the home page, we have identified **top-10 active users** based on the "unnormalized" z-scores of the overall discourse data.



# Contact

For any questions or inquiries, please contact Shubham Gattani (21f3002082@ds.study.iitm.ac.in).
