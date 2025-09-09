"""
Data processing functions for course-specific analytics.
Contains logic for processing/manipulating user actions and generating insights.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


from application.constants import action_to_description, weights_dict_for_course_specific_engagement, weights_dict_for_overall_engagement
import core.data_loader as data_loader
from core.utils import get_current_trimester
from core.execute_query import execute_discourse_query


def create_raw_metrics_dataframe(df):
    """
    This function creates a raw metrics dataframe.
    Steps:
    1. Maps `action_type` values to more descriptive `action_name` values (via action_to_description).
    2. Counts the occurrences of each action type (action_name) per user (acting_username).
    3. Drops certain action types that are not required for analysis.
    4. Returns a dataframe with one row per user and one column per action count.
    """

    # Change the values in action_name column based on values of action_type and map it via the action_to_description dictionary. This is done to make the column_names more intuitive to understand.
    subject_dataframe = df.copy()
    subject_dataframe['action_type'] = subject_dataframe['action_type'].astype(str)
    subject_dataframe['action_name'] = subject_dataframe['action_type'].map(action_to_description)
    subject_dataframe = pd.crosstab(subject_dataframe["acting_username"], subject_dataframe["action_name"]) # Builds a crosstab (pivot table) where: Rows = acting_username (users performing actions; Columns = action_name (types of actions); Values = count of occurrences for each (user, action) combination.

    columns_to_be_dropped = ['linked','received_response', "user's_post_quoted",
        'user_edited_post', 'user_was_mentioned'] # dropping columns which are not required for analysis

    subject_dataframe.drop(columns_to_be_dropped, axis=1, inplace=True, errors='ignore')

    subject_dataframe['acting_username'] = subject_dataframe.index # Changing the index to a column
    subject_dataframe = subject_dataframe[["acting_username"]+[col for col in subject_dataframe.columns if col != 'acting_username']]  # Reordering the columns
    subject_dataframe.index = range(0, len(subject_dataframe))
    subject_dataframe.columns.name = None
    return subject_dataframe # Returns raw metrics dataframe


def create_unnormalized_scores_dataframe(raw_metrics_df): # unnormalised scores
    """
    This function creates an unnormalized scores dataframe.
    The unnormalized scores are calculated by multiplying the raw metrics by their respective weights and summing them up.
    The z-score is then calculated using the initial score.
    The dataframe is then sorted by the z-score in descending order.
    """
    df2 = pd.DataFrame(raw_metrics_df.copy())
    columns_to_be_ignored = ["initial_score",'username','overall_topics_count_of_this_subject', 'normalised_score', 'z_score', "acting_username"] # If some column names seem irrelevant, please ignore them.

    df2["initial_score"] = sum(df2[column]*weights_dict_for_course_specific_engagement[column] for column in df2.columns if column not in columns_to_be_ignored) # Initial score = sum(column_value*weight)

    df2["z_score"] = round((df2["initial_score"] - df2["initial_score"].mean()) / df2["initial_score"].std(),2) # z_score rounded to 2 decimal places
    df2 = df2.sort_values(by="z_score", ascending=False)
    return df2


def create_log_normalized_scores_dataframe(raw_metrics_df):
    feats = [f for f in weights_dict_for_course_specific_engagement if f in raw_metrics_df.columns] # List of features (columns) that are present in the raw_metrics_df

    X = (raw_metrics_df[feats]
         .apply(pd.to_numeric, errors='coerce')
         .fillna(0.0)) # Convert the features to numeric and fill the missing values with 0

    X_log = np.log1p(X)  # no rounding here

    # apply weights
    score = sum(X_log[c] * weights_dict_for_course_specific_engagement[c] for c in feats) # Calculate the log-normalized score
    out = raw_metrics_df.copy() # Create a copy of the raw_metrics_df
    out["log_weighted_score"] = score # Add the log-normalized score to the dataframe

    std = out["log_weighted_score"].std() # Calculate the standard deviation of the log-normalized score
    out["z_score"] = 0.0 if std == 0 else (out["log_weighted_score"] - out["log_weighted_score"].mean()) / std # Calculate the z-score
    out = out.sort_values("z_score", ascending=False) # Sort the dataframe by the z-score in descending order

    # round only if needed for presentation
    out["z_score"] = out["z_score"].round(2)
    return out

def get_course_specific_dataframes(query_params):
    """
    Calls the query_103 using parameters {category_id, start_date, end_date} to get user_actions_df which is then used to create and return 3 dataframes:
    
    1. RAW METRICS: This dataframe simply shows the metrics of each user, e.g likes_given, topics_created etc, for that specific course
    2. UNNORMALIZED_SCORES DF: Sum of [ raw_metric*weightage ]
    3. LOG-NORMALIZED SCORE: Sum of [ log1p(raw_metric) * weightage ]
    """
    query_params = dict(query_params)
    user_actions_df = execute_discourse_query(103, query_params)
    if user_actions_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), ["no topics as of because of very low discourse activity"] # Return 3 empty DFs + one list
    
    raw_metrics_df = create_raw_metrics_dataframe(user_actions_df)
    unnormalized_scores_df = create_unnormalized_scores_dataframe(raw_metrics_df)
    log_normalized_scores_df = create_log_normalized_scores_dataframe(raw_metrics_df)
    return user_actions_df, raw_metrics_df, unnormalized_scores_df, log_normalized_scores_df


def get_top_10_first_responders(course):
    """
    Get top respondents from user actions dataframe for a specific course.
    Put this function in processors.py file in new structure
    """
    term = get_current_trimester()
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    df = (user_actions_dictionaries[term][course]["user_actions_df"]).copy(deep=True)  # Make a copy to avoid modifying the original dataframe
    
    if df.empty:
        raise ValueError("The user actions dataframe is empty, cannot compute top respondents.")
    
    df['created_at'] = pd.to_datetime(df['created_at'])  # Convert created_at to datetime for sorting

    # Step 1: Get all new topics
    new_topics = df[df['action_name'] == 'new_topic'][['target_topic_id', 'topic_title', 'created_at']]

    # Step 2: For each topic, find the first reply/response after the new_topic timestamp
    first_responders = []

    for _, row in new_topics.iterrows():
        topic_id = row['target_topic_id']
        topic_time = row['created_at']
        topic_title = row['topic_title']
        
        # Get replies/responses for this topic AFTER the topic creation time
        replies = df[(df['target_topic_id'] == topic_id) & 
                    (df['action_name'].isin(['reply', 'response'])) &
                    (df['created_at'] > topic_time)]
        
        if not replies.empty:
            first_reply = replies.sort_values('created_at').iloc[0]
            first_responders.append((topic_title, first_reply['acting_username'], first_reply['created_at']))

    # Convert to DataFrame
    first_responders_df = pd.DataFrame(first_responders, columns=['topic_title', 'first_responder', 'response_time'])

    # Count most frequent first responders
    most_freq_first_responders = first_responders_df['first_responder'].value_counts().head(10)
    most_freq_first_responders_list = list(most_freq_first_responders.items())
    return most_freq_first_responders_list


def get_trending_topics_from_useractions_df(course):
    """
    Get trending topics from user actions dataframe for a specific course.
    Put this function in processors.py file in new structure
    """
    term = get_current_trimester()
    user_actions_dictionaries = data_loader.get_user_actions_dictionaries()
    df = (user_actions_dictionaries[term][course]["user_actions_df"]).copy()  # Make a copy to avoid modifying the original dataframe
    
    if df.empty:
        raise ValueError("The user actions dataframe is empty, cannot compute trending topics.")
    
    # Convert created_at to datetime for sorting
    df['created_at'] = pd.to_datetime(df['created_at'], format='mixed')  # Handles UTC & IST

    # Define weights for actions
    weights = {
        'response': 0.5,
        'like': 0.35,
        'quote': 3,
    }

    # 1. Find topics created in the last 7 days
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    seven_days_ago_utc = pd.Timestamp(seven_days_ago, tz='UTC')  # Convert to UTC
    recent_topics = df[(df['action_name'] == 'new_topic') & (df['created_at'] >= seven_days_ago_utc)]
    recent_topic_ids = set(recent_topics['target_topic_id'])

    # 2. Filter actions for these topics (excluding 'new_topic')
    recent_actions = df[(df['target_topic_id'].isin(recent_topic_ids)) &
                        (df['action_name'].isin(weights.keys()))]

    # 3. Group by topic and count actions
    topic_action_counts = recent_actions.groupby(['target_topic_id', 'action_name']).size().unstack(fill_value=0)

    # Preserve original counts before applying weights
    counts_df = topic_action_counts.copy()

    # 4. Compute raw scores using weights
    for action, weight in weights.items():
        if action in topic_action_counts.columns:
            topic_action_counts[action] *= weight

    topic_action_counts['raw_score'] = topic_action_counts.sum(axis=1)

    # 5. Add topic creation time and title
    topic_info = recent_topics.set_index('target_topic_id')[['topic_title', 'created_at']]
    merged = topic_action_counts.merge(topic_info, left_index=True, right_index=True)

    # 6. Normalize by age (in hours)
    now_utc = pd.Timestamp(now, tz='UTC')
    merged['hours_since_creation'] = (now_utc - merged['created_at']).dt.total_seconds() / 3600
    merged['normalized_score'] = merged['raw_score'] / merged['hours_since_creation']

    # Merge counts for final output
    merged = merged.merge(counts_df, left_index=True, right_index=True, suffixes=('', '_count'))

    # 7. Sort and get top 10
    top_trending = merged.sort_values('normalized_score', ascending=False).head(10)

    # Build final output list: (topic_id, topic_url, topic_title, response_count, like_count, quote_count)
    top_trending_list = []
    for topic_id, row in top_trending.iterrows():
        url = f"https://discourse.onlinedegree.iitm.ac.in/t/{topic_id}"
        topic_title = row['topic_title']
        response_count = row.get('response', 0)
        like_count = row.get('like', 0)
        quote_count = row.get('quote', 0)
        top_trending_list.append((topic_id, url, topic_title, int(response_count), int(like_count), int(quote_count)))

    return top_trending_list

