import re, os, time, requests
from datetime import date
import pandas as pd
import numpy as np
from functools import lru_cache
from subject_wise_engagement.execute_query import execute_query_103, execute_query_102
import altair as alt
from datetime import datetime, timedelta
# from execute_query import execute_query_103, execute_query_102

def sanitize_filepath(name):
    # Replace invalid characters with underscore
    return re.sub(r'[<>:"/\\|?* ]', '_', name)

def get_current_trimester():
    today = date.today()
    year = today.year
    month = today.month

    if 1 <= month <= 4:
        trimester = 't1'
    elif 5 <= month <= 8:
        trimester = 't2'
    else:
        trimester = 't3'

    return f"{trimester}-{year}" # e.g "t2-2025"


def get_previous_trimesters(current_trimester):
    trimesters = ['t1', 't2', 't3']
    t, y = current_trimester.split('-')
    year = int(y)
    index = trimesters.index(t)

    result = []
    for _ in range(3):
        index -= 1
        if index < 0:
            index = 2
            year -= 1
        result.append(f"{trimesters[index]}-{year}")
    
    return [current_trimester]+result

action_to_description = {
"1": "likes_given",
"2": "likes_received",
"3": "bookmarked_post",
"4": "created_new_topic",
"5": "replied",
"6": "received_response",
"7": "user_was_mentioned",
"9": "user's_post_quoted",
"11": "user_edited_post",
"12": "user_sent_private_message",
"13": "recieved_a_private_message",
"15": "solved_a_topic",
"16": "user_was_assigned",
"17": "linked"
}


def create_raw_metrics_dataframe(df):
    # Change the values in action_name column based on values of action_type and map it via the action_to_description dictionary. This is done to make the column_names more intuitive to understand.
    subject_dataframe = df.copy()
    subject_dataframe['action_type'] = subject_dataframe['action_type'].astype(str)
    subject_dataframe['action_name'] = subject_dataframe['action_type'].map(action_to_description)
    subject_dataframe.to_csv("TRASH/data/subject_dataframe.csv", index=False) # REMOVE THIS LINE AFTER TESTING
    subject_dataframe = pd.crosstab(subject_dataframe["acting_username"], subject_dataframe["action_name"]) # Creating PIVOT table

    columns_to_be_dropped = ['linked','received_response', "user's_post_quoted",
        'user_edited_post', 'user_was_mentioned'] # dropping columns which are not required for analysis

    subject_dataframe.drop(columns_to_be_dropped, axis=1, inplace=True, errors='ignore')

    subject_dataframe['acting_username'] = subject_dataframe.index # Changing the index to a column
    subject_dataframe = subject_dataframe[["acting_username"]+[col for col in subject_dataframe.columns if col != 'acting_username']]  # Reordering the columns
    subject_dataframe.index = range(0, len(subject_dataframe))
    subject_dataframe.columns.name = None
    return subject_dataframe # Returns raw metrics dataframe


# Assign the weights to the relevant columns. This can be changed as per the requirement.
weights_dict_for_course_specific_engagement = { 'likes_given': 0.3, # 0.3
                "likes_received": 0.8, # changed from 0.7
                "created_new_topic": 0.5, # changed from 1.0
                "replied": 0.7,
                'solved_a_topic': 10 # Highest weight
}


def create_unnormalized_scores_dataframe(df): # unnormalised scores
    df2 = pd.DataFrame(df.copy())
    columns_to_be_ignored = ["initial_score",'username','overall_topics_count_of_this_subject', 'normalised_score', 'z_score', "acting_username"] # If some column names seem irrelevant, please ignore them.

    df2["initial_score"] = sum(df2[column]*weights_dict_for_course_specific_engagement[column] for column in df2.columns if column not in columns_to_be_ignored) # Initial score = sum(column_value*weight)

    df2["z_score"] = round((df2["initial_score"] - df2["initial_score"].mean()) / df2["initial_score"].std(),2) # z_score rounded to 2 decimal places
    return df2.sort_values(by="z_score",ascending=False)


def create_log_normalized_scores_dataframe(df):
    # Apply log normalization to the numerical features
    numerical_features = list(weights_dict_for_course_specific_engagement.keys())
    log_normalized_dataframe = df.copy()
    for feature in numerical_features.copy():
        if feature in df.columns:
            try:
                log_normalized_dataframe[feature] = round(np.log1p(log_normalized_dataframe[feature]),3)
            except Exception as e:
                print(f"\n********Error in log normalization for feature {feature}: {e}\n********\n")
        else:
            numerical_features.remove(feature) # Remove the feature from the list if log normalization fails
            continue
    
    log_normalized_dataframe["initial_score"] = log_normalized_dataframe[numerical_features].sum(axis=1)
    log_normalized_dataframe["z_score"] = round(
        (log_normalized_dataframe["initial_score"] - log_normalized_dataframe["initial_score"].mean()) / log_normalized_dataframe["initial_score"].std(),2)
    return log_normalized_dataframe.sort_values(by="z_score",ascending=False)

# @lru_cache(maxsize=None)
def get_all_course_specific_df(query_params):
    """
    Calls the query_103 using parameters {category_id, start_date, end_date} to get user_actions_df which is then used to create and return 3 dataframes:
    
    1. RAW METRICS: This dataframe simply shows the metrics of each user, e.g likes_given, topics_created etc, for that specific course
    2. UNNORMALIZED_SCORES DF: Sum of [ raw_metric*weightage ]
    3. LOG-NORMALIZED SCORE: Sum of [ log1p(raw_metric) * weightage ]
    4. unique_topic_ids: List of unique topic-ids for that course in the time-frame
    """
    query_params = dict(query_params)
    print(f'Executing query_103 for cat_id={query_params["category_id"]} and dates={query_params["start_date"]}; {query_params["end_date"]}') # REMOVE
    user_actions_df = execute_query_103(103, query_params)
    # user_actions_df.info()
    unique_topic_ids = user_actions_df[user_actions_df["target_post_id"] == -1]["target_topic_id"].unique()
    if user_actions_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [] # Return 3 empty DFs + one empty list
    
    raw_metrics_df = create_raw_metrics_dataframe(user_actions_df)
    unnormalized_scores_df = create_unnormalized_scores_dataframe(raw_metrics_df)
    log_normalized_scores_df = create_log_normalized_scores_dataframe(raw_metrics_df)
    return user_actions_df, raw_metrics_df, unnormalized_scores_df, log_normalized_scores_df, unique_topic_ids

# Assign the weights to the relevant columns. This can be changed as per the requirement.
weights_dict_for_overall_engaagement = { 'likes_given': 0.4, # likes_given is also important
                "likes_received": 0.8,
                "topics_created": 0.4,
                "posts_created": 0.7,
                "days_visited": 0.3, # decreased weightage because it is a very common action
                'solutions': 10,
}

def create_unnormalized_scores_dataframe_for_all_users(df_original):
    df = df_original.copy()
    df["initial_score"] = sum(df[column]*weights_dict_for_overall_engaagement[column] for column in df.columns if column not in ["user_id"]) # Initial score = sum(column_value*weight)

    df["z_score"] = round((df["initial_score"] - df["initial_score"].mean()) / df["initial_score"].std(),2) # z_score rounded to 2 decimal places
    return df.sort_values(by="z_score",ascending=False)


def create_log_normalized_scores_dataframe_for_all_users(df):
    # Apply log normalization to the numerical features
    numerical_features = list(weights_dict_for_overall_engaagement.keys())
    log_normalized_dataframe = df.copy()
    for feature in numerical_features:
        log_normalized_dataframe[feature] = round(np.log1p(log_normalized_dataframe[feature]),3)
    
    log_normalized_dataframe["initial_score"] = log_normalized_dataframe[numerical_features].sum(axis=1)
    log_normalized_dataframe["z_score"] = round((log_normalized_dataframe["initial_score"] - log_normalized_dataframe["initial_score"].mean()) / log_normalized_dataframe["initial_score"].std(),2)
    return log_normalized_dataframe.sort_values(by="z_score",ascending=False)

# @lru_cache(maxsize=None)
def get_overall_engagement_df(query_params):
    query_params = dict(query_params)
    print(f'Executing query_102 (for all users data) for dates={query_params["start_date"]}; {query_params["end_date"]}') # REMOVE
    raw_metrics_df = execute_query_102(102, query_params = query_params)
    if raw_metrics_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    raw_metrics_df = raw_metrics_df[["user_id"] + list(weights_dict_for_overall_engaagement.keys())]
    unnormalized_scores_dataframe, log_normalized_scores_dataframe = create_unnormalized_scores_dataframe_for_all_users(raw_metrics_df), create_log_normalized_scores_dataframe_for_all_users(raw_metrics_df)
    return raw_metrics_df, unnormalized_scores_dataframe, log_normalized_scores_dataframe



# @lru_cache(maxsize=None)
def get_top_10_first_responders(topic_list):
    headers = {
                "Api-Key": os.environ.get('API_KEY'),
                "Api-Username": "shubhamg"
           }
    # print("HEADERS = ", headers)
    most_frequent_users = {}
    for t in topic_list:
        try:
            response = requests.get(
                url = f"https://discourse.onlinedegree.iitm.ac.in/t/{t}.json",
                headers=headers
                            )
            D = response.json()
            posts = D["post_stream"]["posts"] # List of dicts each having details of each post of that topic
            for post in posts:
                if post["post_number"]==2: # If it is the second post in that topic, meaning the first response to that topic
                    username = post["username"] # Find the username of the first responder
                    most_frequent_users[username] = most_frequent_users.get(username,0)+1 # Increment the frequqncy of first-responder
            time.sleep(0.9)
        except Exception as e:
            print(f"Encountered an ERROR {e} when trying to find details for the topic {t}")
            continue

    sorted_users = sorted(most_frequent_users.items(), key=lambda x: x[1], reverse=True)
    top_10_first_responders = sorted_users[:10] # Note that this is a list of tuples
    return top_10_first_responders


def get_trimester_week(date_str):
    """
    Given a date string in 'YYYY-MM-DD', returns:
    (trimester_number, week_in_trimester, week_start_date, week_end_date)
    
    Week start and end dates are in format 'dd-mm-yyyy'.
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    year = date.year

    # Define trimester start dates
    t1_start = datetime(year, 1, 1)
    t2_start = datetime(year, 5, 1)
    t3_start = datetime(year, 9, 1)

    if date < t2_start:
        trimester = 1
        trimester_start = t1_start
    elif date < t3_start:
        trimester = 2
        trimester_start = t2_start
    else:
        trimester = 3
        trimester_start = t3_start

    days_diff = (date - trimester_start).days
    week_in_trimester = days_diff // 7 + 1  # 1-based week number

    # Calculate week start and end dates
    week_start = trimester_start + timedelta(weeks=week_in_trimester - 1)
    week_end = week_start + timedelta(days=6)

    # Format the dates as 'dd-mm-yyyy'
    week_start_str = week_start.strftime("%d-%m-%Y")
    week_end_str = week_end.strftime("%d-%m-%Y")

    return f"t{trimester}-w{week_in_trimester};  ({week_start_str}, {week_end_str})"

def create_weekwise_engagement(df):
    df["created_at"] = df["created_at"].map(lambda x: x.split("T")[0])
    df["week_number"] = df["created_at"].map(lambda x: get_trimester_week(x))

    action_to_description = {
    "1": "total likes",
    "2": "likes_received",
    "3": "bookmarked_post",
    "4": "new topics created",
    "5": "total replies",
    "6": "received_response",
    "7": "user_was_mentioned",
    "9": "user's_post_quoted",
    "11": "user_edited_post",
    "12": "user_sent_private_message",
    "13": "recieved_a_private_message",
    "15": "topics solved",
    "16": "user_was_assigned",
    "17": "linked"
}

    df["action_name_new"] = df["action_type"].astype(str).map(action_to_description)
    df2 = df[["week_number", "action_name_new"]]

    # Create a pivot table
    pivot_table = pd.pivot_table(
        df2,
        index="week_number",  # Rows
        columns="action_name_new",  # Columns
        aggfunc="size",  # Count occurrences
        fill_value=0  # Fill missing values with 0
    )
    # Remove the specified columns from the pivot table
    columns_to_be_removed = ["user_edited_post", "likes_received", "linked", "received_response", "user's_post_quoted", "user_was_mentioned", "user_edited_post"]
    pivot_table = pivot_table.drop(columns=columns_to_be_removed, errors='ignore')
    pivot_table["total_score"] = pivot_table.apply(lambda row: sum(row[col] for col in pivot_table.columns), axis=1)

    # Reset the index of the pivot_table to make "week_number" a column
    pivot_table_reset = pivot_table.reset_index()

    # Sort by total_score in descending order
    pivot_table_reset = pivot_table_reset.sort_values(by="total_score", ascending=False)

    # Combine all metric details into a single string for display in the tooltip
    pivot_table_reset["metrics_details"] = pivot_table_reset.apply(
        lambda row: "\n".join([f"{col}:{row[col]} | " for col in pivot_table.columns if col != "total_score"]),
        axis=1
    )

    # Create the heatmap
    heatmap = alt.Chart(pivot_table_reset).mark_rect().encode(
        x=alt.X(
            'week_number:O', 
            title='Week Number (start:end)', 
            sort=pivot_table_reset["week_number"].tolist(),
            axis=alt.Axis(labelAngle=45)  # Set label angle here
        ),
        y=alt.Y('total_score:Q', title='Total Score'),
        color=alt.Color('total_score:Q', title='Total Score', scale=alt.Scale(scheme='greens')),
        tooltip=[
            alt.Tooltip('week_number:O', title='Week Number'),
            alt.Tooltip('total_score:Q', title='Total Score'),
            alt.Tooltip('metrics_details:N', title='Metrics Details')
        ]
    ).properties(
        width=700,
        # height=400,
        title="Heatmap of Total Score by Week Number"
    )

    return heatmap