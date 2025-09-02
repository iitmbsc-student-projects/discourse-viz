import requests, time, math, json, os
import pandas as pd
import altair as alt
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from functools import lru_cache

base_url = "https://discourse.onlinedegree.iitm.ac.in"

API_KEY = os.environ.get("API_KEY")
API_USERNAME = "ShubhamG"

def get_user_summary(user_name):
    url = f"{base_url}/u/{user_name}/summary.json"
    print(url)

    headers = {
        "Api-Key": API_KEY,
        "Api-Username": API_USERNAME
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"error": f"Failed to fetch data for user_id: {user_name}", "status_code": response.status_code}

    data = response.json()
    return data


def get_basic_metrics(summary_data):

    user_summary = summary_data.get("user_summary", {})

    fields_to_show = [
        "likes_given", "likes_received", "topics_entered", "posts_read_count", "days_visited",
        "topic_count", "post_count", "time_read", "recent_time_read", "solved_count"
    ]

    filtered_summary = {key: user_summary[key] for key in fields_to_show if key in user_summary}

    basic_metrics = pd.DataFrame(filtered_summary.items(), columns=["Metric", "Value"])
    basic_metrics.style.set_properties(**{'text-align': 'left'}).set_table_styles(
        [{'selector': 'th', 'props': [('text-align', 'left')]}]
    )
    return basic_metrics

def get_top_categories(summary_data):
    top_categories = summary_data.get("user_summary", {}).get("top_categories", [])

    category_summary = [
        {
            "Course Name": category["name"],
            "Topics Created": category["topic_count"],
            "Posts Replied": category["post_count"]
        }
        for category in top_categories
    ]

    df_categories = pd.DataFrame(category_summary)

    return df_categories

def get_liked_by_users(summary_data):
    liked_by_users = summary_data.get("user_summary", {}).get("most_liked_by_users", [])

    liked_by_summary = [
        {
            "Name": user.get("name", "N/A"),
            "Likes Given To You": user.get("count", 0)
        }
        for user in liked_by_users
    ]

    df_liked_by = pd.DataFrame(liked_by_summary)

    return df_liked_by


def create_stacked_bar_chart(raw_metrics, subject):
    # Assuming raw_metrics is already loaded
    metrics = ['created_new_topic', 'likes_given', 'likes_received', 'replied', 'solved_a_topic']
    # Only use metrics that exist in the DataFrame
    metrics = [m for m in metrics if m in raw_metrics.columns]
    

    # Filter out metrics where all users have value 0
    filtered_metrics = raw_metrics.set_index('acting_username')[metrics].loc[:, (raw_metrics[metrics] != 0).any()]

    if not filtered_metrics.empty:
        # Convert to long format for Altair
        raw_metrics_long = raw_metrics.melt(id_vars=['acting_username'], 
                                            value_vars=metrics, 
                                            var_name='Activity Type', 
                                            value_name='Count')

        # Create Altair stacked bar chart
        chart = alt.Chart(raw_metrics_long).mark_bar().encode(
            x=alt.X('Count:Q', title="Total User Interactions",
                    axis=alt.Axis(titleFontSize=14)),
            y=alt.Y('acting_username:N', title="Username", sort='-x',
                    axis=alt.Axis(titleFontSize=14)),
            color=alt.Color('Activity Type:N', title="Activity Type"),
            tooltip=['acting_username', 'Activity Type', 'Count']
        ).properties(
            title=f'User activity for ({subject})',
            width=600,
            height=400
        ).configure_legend(
            orient='right'
        )
        return chart
    else:
        text="""EMPTY CHART"""
        # Create a dummy dataframe with a single row
        df = pd.DataFrame({'x': [0], 'y': [0], 'text': [text]})

        # Create the chart
        chart = alt.Chart(df).mark_text(
            align='center',
            baseline='middle',
            fontSize=18,
            color='gray'
        ).encode(
            x=alt.value(250),  # X position in pixels
            y=alt.value(150),  # Y position in pixels
            text='text:N'
        ).properties(
            width=500,
            height=300
        )

        return chart

def fetch_recent_topics(slug = "stats2-kb", id=24):
    """
    Fetches recent discussion topics from a specified Discourse category within a defined time window (default: last 7 days).

    Parameters:
    - slug (str): The category slug used in the Discourse URL (default: "stats2-kb").
    - id (int): The numeric category ID for the Discourse category (default: 24).

    Returns:
    - dict: A dictionary containing details of topics created within the last 7 days, with keys:
        - "id": List of topic IDs.
        - "title": List of topic titles.
        - "created_at": List of creation timestamps (ISO format).
        - "posts_count": List of post counts per topic.
        - "reply_count": List of reply counts per topic.
        - "views": List of view counts per topic.
        - "like_count": List of like counts per topic.
        - "has_accepted_answer": List of boolean values indicating if the topic has an accepted answer.

    Behavior:
    - Fetches up to 3 pages of topics from the specified category.
    - Filters topics created within the last 7 days based on current UTC time.
    - Skips topics without a "created_at" field.
    - Prevents duplicate topic entries.
    - Introduces a short delay (0.9 seconds) between page requests to avoid rate-limiting.
    - Prints debug messages when encountering errors, duplicate topics, or empty pages.
    """
    today_str = datetime.today().strftime("%d-%m-%Y") # Today's date in string format dd-mm-yyyy
    page=0
    last_10_days_topic_details = {"id":[]}
    days_limit = 7
    now = datetime.strptime(today_str, "%d-%m-%Y").replace(tzinfo=timezone.utc)
    page = 0
    headers = {
        "Api-Key": API_KEY,
        "API_USERNAME" : API_USERNAME,
    }

    while page<3:
        base_url = f"https://discourse.onlinedegree.iitm.ac.in/c/{slug}/{id}.json?page={page}"
        resp = requests.get(base_url, headers = headers)
        if resp.status_code != 200:
            resp.raise_for_status() # Raise an HTTPError for bad responses
            break
        info_dict = resp.json()
        topics = info_dict.get("topic_list", {}).get("topics", [])

        for topic in topics:
            created_at = topic.get("created_at")
            if not created_at:
                continue
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if (now - created_dt).days < days_limit:
                topic_id = topic.get("id", None)
                if topic_id not in last_10_days_topic_details["id"]:
                    last_10_days_topic_details.setdefault("id", []).append(topic_id)
                    last_10_days_topic_details.setdefault("title", []).append(topic.get("title", None))
                    last_10_days_topic_details.setdefault("created_at", []).append(topic.get("created_at", None))
                    last_10_days_topic_details.setdefault("posts_count", []).append(topic.get("posts_count", None))
                    last_10_days_topic_details.setdefault("reply_count", []).append(topic.get("reply_count", None))
                    last_10_days_topic_details.setdefault("views", []).append(topic.get("views", None))
                    last_10_days_topic_details.setdefault("like_count", []).append(topic.get("like_count", None))
                    last_10_days_topic_details.setdefault("has_accepted_answer", []).append(topic.get("has_accepted_answer", None))
                else:
                    print(f"Repeated topic found for {base_url}")

        if not topics:
            print(f"Breaking earlier at page = {page} because no topics left")
            break
        page += 1
        time.sleep(0.9)

    return last_10_days_topic_details

def compute_trending_scores(data: Dict):
    """
    Computes trending scores for topics based on views, posts, and likes, adjusted for recency.
    Applies time-based decay and log normalization to prevent skew from outliers.
    Returns the top 10 topics with details like URL, title, and solved status.
    Useful for ranking discussion topics in online forums dynamically.
    """
    # Define weights for different engagement metrics
    weights = {
        "views": 0.15,        # Weight for number of views
        "posts_count": 0.5,   # Weight for number of posts
        "like_count": 0.35    # Weight for number of likes
    }

    # Get the current time in UTC
    now = datetime.now(timezone.utc)

    # This list will store tuples containing (score, topic details)
    scores = []

    # Loop through each topic in the dataset
    for i in range(len(data["created_at"])):
        # Convert the created_at string to a datetime object (handling the "Z" UTC marker)
        created_at = datetime.fromisoformat(data["created_at"][i].replace("Z", "+00:00"))
        
        # Calculate topic's age in hours
        age_hours = (now - created_at).total_seconds() / 3600
        age_hours = max(age_hours, 1)  # Avoid division by zero or giving huge advantage to very new topics

        # Normalize each metric by time (per hour)
        views_per_hour = data["views"][i] / age_hours
        posts_per_hour = data["posts_count"][i] / age_hours
        likes_per_hour = data["like_count"][i] / age_hours

        # Apply log normalization to reduce skew from very large values
        norm_views = math.log1p(views_per_hour)   # log(1 + views/hour)
        norm_posts = math.log1p(posts_per_hour)   # log(1 + posts/hour)
        norm_likes = math.log1p(likes_per_hour)   # log(1 + likes/hour)

        # Compute the final weighted score for the topic
        score = (
            weights["views"] * norm_views +
            weights["posts_count"] * norm_posts +
            weights["like_count"] * norm_likes
        )

        # Prepare additional details for output
        topics_url = f"https://discourse.onlinedegree.iitm.ac.in/t/{data['id'][i]}"
        solved_or_not = data["has_accepted_answer"][i]
        topic_title = data["title"][i]
        views = data["views"][i]
        like_count = data["like_count"][i]

        # Add the result tuple to the list
        scores.append((score, data["id"][i], topics_url, topic_title, solved_or_not, views, like_count))
    
    # Sort the list by score in descending order
    scores.sort(reverse=True, key=lambda x: x[0])

    # Return the top 10 trending topics
    return scores[:10]




if __name__ == "__main__":
    user_name = "shubhamg"
    # summary_data = get_user_summary(user_name)
    # basic_metrics, top_categories, most_liked_by = get_basic_metrics(summary_data), get_top_categories(summary_data), get_liked_by_users(summary_data)
    # print(basic_metrics, top_categories, most_liked_by, sep="\n\n***********\n\n")
    # print(get_user_email(user_name))