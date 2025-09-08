import requests
import pandas as pd

from constants import API_USERNAME, API_KEY, DISCOURSE_BASE_URL


def get_user_summary(user_name):
    url = f"{DISCOURSE_BASE_URL}/u/{user_name}/summary.json"
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
