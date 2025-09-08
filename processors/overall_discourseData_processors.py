import pandas as pd
import numpy as np
from core.execute_query import execute_discourse_query
import altair as alt

from constants import weights_dict_for_overall_engagement

def create_unnormalized_scores_dataframe_for_all_users(raw_metrics_df):
    """
    This function creates an unnormalized scores dataframe for all users.
    It takes the raw metrics dataframe as input and returns the unnormalized scores dataframe.
    The unnormalized scores are calculated by multiplying the raw metrics by their respective weights and summing them up.
    The z-score is then calculated using the initial score.
    The dataframe is then sorted by the z-score in descending order.
    """
    df = raw_metrics_df.copy()
    df["initial_score"] = sum(df[column]*weights_dict_for_overall_engagement[column] for column in df.columns if column not in ["user_id"]) # Initial score = sum(column_value*weight)

    df["z_score"] = round((df["initial_score"] - df["initial_score"].mean()) / df["initial_score"].std(),2) # z_score rounded to 2 decimal places
    return df.sort_values(by="z_score",ascending=False)


def create_log_normalized_scores_dataframe_for_all_users(raw_metrics_df):
    """
    This function creates a log-normalized scores dataframe for all users.
    It takes the raw metrics dataframe as input and returns the log-normalized scores dataframe.
    The log-normalized scores are calculated by applying the log1p function to the numerical features and summing them up.
    The z-score is then calculated using the initial score.
    The dataframe is then sorted by the z-score in descending order.
    """
    numerical_features = list(weights_dict_for_overall_engagement.keys())
    log_normalized_dataframe = raw_metrics_df.copy()
    for feature in numerical_features:
        log_normalized_dataframe[feature] = round(np.log1p(log_normalized_dataframe[feature]),3) 
    
    log_normalized_dataframe["initial_score"] = log_normalized_dataframe[numerical_features].sum(axis=1)
    log_normalized_dataframe["z_score"] = round((log_normalized_dataframe["initial_score"] - log_normalized_dataframe["initial_score"].mean()) / log_normalized_dataframe["initial_score"].std(),2)
    return log_normalized_dataframe.sort_values(by="z_score",ascending=False)

def get_overall_engagement_df(query_params):
    """
    This function is used to get the overall engagement dataframe for all users.
    It calls the query_102 using parameters {start_date, end_date} to get the raw metrics dataframe.
    It then creates the unnormalized and log-normalized scores dataframes.
    Returns:
        raw_metrics_df: Raw metrics dataframe for all users
        unnormalized_scores_dataframe: Unnormalized scores dataframe for all users
        log_normalized_scores_dataframe: Log-normalized scores dataframe for all users
    """
    query_params = dict(query_params)
    raw_metrics_df = execute_discourse_query(102, query_params = query_params)
    if raw_metrics_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    raw_metrics_df = raw_metrics_df[["user_id"] + list(weights_dict_for_overall_engagement.keys())]
    unnormalized_scores_dataframe, log_normalized_scores_dataframe = create_unnormalized_scores_dataframe_for_all_users(raw_metrics_df), create_log_normalized_scores_dataframe_for_all_users(raw_metrics_df)
    return raw_metrics_df, unnormalized_scores_dataframe, log_normalized_scores_dataframe
