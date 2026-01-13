import pandas as pd
from core.utils import sanitize_filepath, get_current_trimester, get_previous_trimesters
from datetime import datetime

from application.constants import weights_dict_for_overall_engagement, env
from core.execute_query import execute_discourse_query
from processors.course_data_processors import (create_raw_metrics_dataframe,
                                     create_unnormalized_scores_dataframe,create_log_normalized_scores_dataframe)

from processors.overall_discourseData_processors import (
                                create_log_normalized_scores_dataframe_for_all_users, create_unnormalized_scores_dataframe_for_all_users)

# Global state (initialized by init_minimal_data / background_load_user_actions)
user_actions_dictionaries = {}
df_map_category_to_id = None
id_username_mapping = None
user_actions_loaded = False
last_refresh_date = datetime.now().strftime("%d-%m-%Y")

# DATA LOADER FUNCTIONS
def load_user_actions_dictionaries():
    from core.data_processor import get_all_data_dicts
    data_dicts = get_all_data_dicts()
    return data_dicts

def load_df_map_category_to_id():
    irrelevant_categories = [63,64,79,80,86,87,88,91,95,96,97,103,104,105,106,107,
                             112,113,114,49,50,51,52,102,121,120]
    if env=="dev":
        df_map_category_to_id = pd.read_csv("TRASH/data/df_map_category_to_id.csv")
        df_map_category_to_id = df_map_category_to_id[~df_map_category_to_id["category_id"].isin(irrelevant_categories)]
    else:
        df_map_category_to_id = execute_discourse_query(query_id=107, query_params=None)
        df_map_category_to_id = df_map_category_to_id[~df_map_category_to_id["category_id"].isin(irrelevant_categories)]
    return df_map_category_to_id

def load_id_username_mapping():
    from core.execute_query import execute_discourse_query
    if env=="dev":
        df = pd.read_csv("TRASH/data/id_username_mapping.csv") # FOR TESTING ONLY
    else:
        df = execute_discourse_query(query_id=108, query_params=None)
    return df

def init_minimal_data():
    global df_map_category_to_id, id_username_mapping, user_actions_dictionaries
    df_map_category_to_id = load_df_map_category_to_id()  # ~1 min
    id_username_mapping = load_id_username_mapping()      # ~1 min

    # Create empty placeholders based on category IDs and current terms
    current_and_prev_terms = get_previous_trimesters(get_current_trimester())[:3]
    user_actions_dictionaries = {
        term: {
            sanitize_filepath(row.name).lower(): {
                "user_actions_df": pd.DataFrame(),
                "raw_metrics": pd.DataFrame(),
                "unnormalized_scores": pd.DataFrame(),
                "log_normalized_scores": pd.DataFrame()
            } for row in df_map_category_to_id.itertuples()
        }
        for term in current_and_prev_terms
    }
    print(f"Keys in user_actions_dictionaries after minimal init: {list(user_actions_dictionaries.keys())}")
    return df_map_category_to_id, id_username_mapping, user_actions_dictionaries

def background_load_user_actions():
    global user_actions_dictionaries, user_actions_loaded
    print("Before background load:", user_actions_loaded)
    print("Starting background loading of user_actions_dictionaries...")
    user_actions_dictionaries = load_user_actions_dictionaries()  # ~20 min
    user_actions_loaded = True
    print("Background loading completed.")
    print("After background load:", user_actions_loaded)
    return user_actions_dictionaries

def get_user_actions_loaded():
    """Helper function to check if user actions are loaded"""
    return user_actions_loaded

def get_user_actions_dictionaries():
    """Helper function to get user actions dictionaries"""
    return user_actions_dictionaries

def get_df_map_category_to_id():
    """Helper function to get category mapping"""
    return df_map_category_to_id

def get_id_username_mapping():
    """Helper function to get username mapping"""
    return id_username_mapping


# DATA REFRESH FUNCTION
def refresh_all_data():
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping, last_refresh_date
    today = datetime.now().strftime("%d-%m-%Y")
    trimester_corresponding_to_today = get_current_trimester()
    trimester_data_to_be_removed = get_previous_trimesters(trimester_corresponding_to_today)[3]
    user_actions_dictionaries.pop(trimester_data_to_be_removed, None)
    print("User actions dictionaries keys: ", user_actions_dictionaries.keys())

    # NEW: Initialize new trimester if it doesn't exist; BUG fixed on 28-DEC-2025
    if trimester_corresponding_to_today not in user_actions_dictionaries:
        print(f"New trimester detected: {trimester_corresponding_to_today}. Initializing structure...")
        user_actions_dictionaries[trimester_corresponding_to_today] = {}
        
        # Initialize course structures
        for row in df_map_category_to_id.itertuples():
            category_name = sanitize_filepath(row.name).lower()
            user_actions_dictionaries[trimester_corresponding_to_today][category_name] = {
                "user_actions_df": pd.DataFrame(),
                "raw_metrics": pd.DataFrame(),
                "unnormalized_scores": pd.DataFrame(),
                "log_normalized_scores": pd.DataFrame()
            }
        
        # Initialize overall engagement structure
        user_actions_dictionaries[trimester_corresponding_to_today]["overall"] = {
            "raw_metrics": pd.DataFrame(),
            "unnormalized_scores": pd.DataFrame(),
            "log_normalized_scores": pd.DataFrame()
        }
    # Creating new data for each course
    for row in df_map_category_to_id.itertuples():
        category_id = row.category_id
        category_name = sanitize_filepath(row.name).lower()
        if category_name not in user_actions_dictionaries[trimester_corresponding_to_today]:
            print(f"Inside refresh function for date = {today}\n{category_name} not found in user_actions_dictionaries for trimester {trimester_corresponding_to_today}")
            continue
        query_params_for_103 = {"category_id": str(category_id), "start_date": last_refresh_date, "end_date": today}

        latest_user_actions_df = execute_discourse_query(103, query_params=query_params_for_103)
        print(f"Inside refresh function for date = {today}\nLatest user actions dataframe for {category_name} has {len(latest_user_actions_df)} rows")
        if not latest_user_actions_df.empty:
            existing_user_actions_df = user_actions_dictionaries[trimester_corresponding_to_today][category_name]["user_actions_df"]
            new_user_actions_df = pd.concat([existing_user_actions_df, latest_user_actions_df]).drop_duplicates()
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["user_actions_df"] = new_user_actions_df

            new_raw_metrics_dataframe = create_raw_metrics_dataframe(new_user_actions_df)
            new_unnormalized_scores_df = create_unnormalized_scores_dataframe(new_raw_metrics_dataframe)
            new_log_normalized_scores_df = create_log_normalized_scores_dataframe(new_raw_metrics_dataframe)

            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["raw_metrics"] = new_raw_metrics_dataframe
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["unnormalized_scores"] = new_unnormalized_scores_df
            user_actions_dictionaries[trimester_corresponding_to_today][category_name]["log_normalized_scores"] = new_log_normalized_scores_df
            
    # Updating data for overall engagement
    query_params_for_102 = {"start_date": last_refresh_date, "end_date": today, "domain":"ds.study.iitm.ac.in"}
    latest_raw_metrics_for_overall_engagement = execute_discourse_query(102, query_params = query_params_for_102)
    existing_raw_metrics_for_overall_engagement = user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["raw_metrics"]

    new_raw_metrics_for_overall_engagement = pd.concat([latest_raw_metrics_for_overall_engagement, existing_raw_metrics_for_overall_engagement]).drop_duplicates()
    new_raw_metrics_for_overall_engagement = new_raw_metrics_for_overall_engagement.groupby("user_id", as_index=False).sum()
    new_raw_metrics_for_overall_engagement = new_raw_metrics_for_overall_engagement[["user_id"] + list(weights_dict_for_overall_engagement.keys())]

    new_unnormalized_scores_dataframe_all_users, new_log_normalized_scores_dataframe_all_users = create_unnormalized_scores_dataframe_for_all_users(new_raw_metrics_for_overall_engagement), create_log_normalized_scores_dataframe_for_all_users(new_raw_metrics_for_overall_engagement)

    user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["raw_metrics"] = new_raw_metrics_for_overall_engagement
    user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["unnormalized_scores"] = new_unnormalized_scores_dataframe_all_users
    user_actions_dictionaries[trimester_corresponding_to_today]["overall"]["log_normalized_scores"] = new_log_normalized_scores_dataframe_all_users

    last_refresh_date = today
    print(f"Data refreshed successfully for {trimester_corresponding_to_today} trimester. Last refresh date is now set to {last_refresh_date}.")
