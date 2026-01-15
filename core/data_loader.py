import pandas as pd
from core.utils import sanitize_filepath, get_current_trimester, get_previous_trimesters, is_trimester_start_today
from datetime import datetime
from core.logging_config import get_logger
from itertools import chain
from application.constants import (
    weights_dict_for_overall_engagement,
    env,
    foundation_courses,
    diploma_programming_courses,
    diploma_data_science_courses,
    core_degree_courses,
    degree_level_courses,
    L4_degree_courses,
    L5_degree_courses,
)
from core.execute_query import execute_discourse_query
from processors.course_data_processors import (
    create_raw_metrics_dataframe,
    create_unnormalized_scores_dataframe,
    create_log_normalized_scores_dataframe,
)
from processors.overall_discourseData_processors import (
    create_log_normalized_scores_dataframe_for_all_users,
    create_unnormalized_scores_dataframe_for_all_users,
)

logger = get_logger("core.data_loader")

# Global state (initialized by init_minimal_data / background_load_user_actions)
user_actions_dictionaries = {}
df_map_category_to_id = None
id_username_mapping = None
user_actions_loaded = False
last_refresh_date = datetime.now().strftime("%d-%m-%Y")
uncategorized_courses = []  # New global list to store uncategorized courses

# Backup state for fallback on full_system_reset failure
# Stores previous state so users can access old data if reset fails
_backup_user_actions_dictionaries = None
_backup_df_map_category_to_id = None
_backup_id_username_mapping = None
_backup_last_refresh_date = None

# Flag to indicate full system reset failure - used by alerting mechanism
system_reset_failed = False
system_reset_failure_reason = None

# DATA LOADER FUNCTIONS
def load_user_actions_dictionaries():
    from core.data_processor import get_all_data_dicts

    data_dicts = get_all_data_dicts()
    return data_dicts


def load_df_map_category_to_id():
    global uncategorized_courses

    irrelevant_categories = [63, 64, 79, 80, 86, 87, 88, 91, 95, 96, 97, 103, 104, 105, 106, 107, 112, 113, 114, 49, 50, 51, 52, 102, 121, 120]
    if env == "dev":
        df_map_category_to_id = pd.read_csv("TRASH/data/df_map_category_to_id.csv")
        df_map_category_to_id = df_map_category_to_id[~df_map_category_to_id["category_id"].isin(irrelevant_categories)]
    else:
        df_map_category_to_id = execute_discourse_query(query_id=107, query_params=None)
        df_map_category_to_id = df_map_category_to_id[~df_map_category_to_id["category_id"].isin(irrelevant_categories)]

    # Create union of all known courses (case-insensitive)
    all_known_courses = set(
        course.strip().lower()
        for course in chain(
            foundation_courses,
            diploma_programming_courses,
            diploma_data_science_courses,
            core_degree_courses,
            degree_level_courses,
            L4_degree_courses,
            L5_degree_courses,
        )
    )

    # Find uncategorized courses
    uncategorized_courses = [
        row.name
        for row in df_map_category_to_id.itertuples()
        if row.name.strip().lower() not in all_known_courses
    ]

    logger.info(f"Found {len(uncategorized_courses)} uncategorized courses | function: load_df_map_category_to_id")

    return df_map_category_to_id


def load_id_username_mapping():
    from core.execute_query import execute_discourse_query

    if env == "dev":
        df = pd.read_csv("TRASH/data/id_username_mapping.csv")  # FOR TESTING ONLY
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
    logger.info(f"Initialized data structures | function: init_minimal_data | terms: {list(user_actions_dictionaries.keys())}")
    return df_map_category_to_id, id_username_mapping, user_actions_dictionaries


def background_load_user_actions():
    global user_actions_dictionaries, user_actions_loaded
    logger.info(f"Starting data loading | function: background_load_user_actions | user_actions_loaded_before: {user_actions_loaded}")
    logger.info(f"Background loading started | function: background_load_user_actions")
    user_actions_dictionaries = load_user_actions_dictionaries()  # ~30 min
    user_actions_loaded = True
    logger.info(f"Background loading completed | function: background_load_user_actions | user_actions_loaded_after: {user_actions_loaded}")
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


def get_uncategorized_courses():
    """Helper function to get uncategorized courses"""
    return uncategorized_courses


def get_system_reset_status():
    """
    Get current status of full system reset.
    
    Returns:
        dict: Contains:
            - 'reset_failed' (bool): Whether the last reset failed
            - 'failure_reason' (str): Error message if reset failed
            - 'requires_investigation' (bool): Whether developer action is needed
    
    This can be used by frontend to show status alerts or by monitoring systems
    to trigger automatic escalations.
    """
    return {
        'reset_failed': system_reset_failed,
        'failure_reason': system_reset_failure_reason,
        'requires_investigation': system_reset_failed
    }


def _backup_current_state():
    """
    Create a backup of current data before full system reset.
    
    This is used as a fallback if the reset fails - allows users to continue
    accessing old data instead of experiencing complete system downtime.
    """
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping, last_refresh_date
    global _backup_user_actions_dictionaries, _backup_df_map_category_to_id, _backup_id_username_mapping, _backup_last_refresh_date
    
    import copy
    
    # Deep copy current state to preserve it in case reset fails
    _backup_user_actions_dictionaries = copy.deepcopy(user_actions_dictionaries)
    _backup_df_map_category_to_id = df_map_category_to_id.copy() if df_map_category_to_id is not None else None
    _backup_id_username_mapping = id_username_mapping.copy() if id_username_mapping is not None else None
    _backup_last_refresh_date = last_refresh_date
    
    logger.info("State backup created | function: _backup_current_state")


def _restore_from_backup():
    """
    Restore data from backup in case full system reset fails.
    
    This ensures users can access old data instead of experiencing complete downtime.
    The system will show old data while developers investigate the reset failure.
    """
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping, last_refresh_date
    global _backup_user_actions_dictionaries, _backup_df_map_category_to_id, _backup_id_username_mapping, _backup_last_refresh_date
    
    user_actions_dictionaries = _backup_user_actions_dictionaries
    df_map_category_to_id = _backup_df_map_category_to_id
    id_username_mapping = _backup_id_username_mapping
    last_refresh_date = _backup_last_refresh_date
    
    logger.info("State restored from backup | function: _restore_from_backup")


def _alert_developer_of_reset_failure(error_message):
    """
    Alert developer about full system reset failure via email/g-chat.
    
    This function should be implemented to send notifications to the development team
    so they can investigate the issue while users continue accessing old data.
    
    Current implementation: PLACEHOLDER - developers should implement email/g-chat alerts
    
    Possible implementations:
    1. Send email via SMTP (gmail, AWS SES, etc.)
    2. Post message to Google Chat webhook
    3. Send Slack notification
    4. Create Jira ticket automatically
    5. Log to monitoring service (Datadog, New Relic, etc.)
    
    Args:
        error_message (str): Description of the reset failure
    """
    # PLACEHOLDER: Implement your alert mechanism here
    # Example for Google Chat:
    # import requests
    # webhook_url = os.environ.get('GOOGLE_CHAT_WEBHOOK_URL')
    # message = {
    #     'text': f'🚨 ALERT: Full System Reset Failed\n\n'
    #             f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    #             f'Error: {error_message}\n\n'
    #             f'Action: Check logs at discourse-viz server'
    # }
    # requests.post(webhook_url, json=message)
    
    logger.warning(f"DEVELOPER ALERT: Full system reset failed | error: {error_message} | function: _alert_developer_of_reset_failure")
    logger.warning("TODO: Implement email/g-chat alerting in _alert_developer_of_reset_failure()")


def full_system_reset():
    """
    Perform a complete system reset - equivalent to application restart.
    
    This function is triggered ONLY on trimester start dates (Jan 1, May 1, Sep 1).
    It recalculates EVERYTHING from scratch:
    - Reloads df_map_category_to_id (Query #107) to discover new courses
    - Reloads id_username_mapping (Query #108) to discover new users
    - Rebuilds all user_actions_dictionaries for current and previous 2 trimesters
    
    This ensures that at the beginning of each trimester:
    1. New courses added to Discourse are discovered and included
    2. New users who enrolled are captured
    3. All engagement data is recalculated with fresh data
    4. No stale or incremental data remains
    
    FAILURE HANDLING (Recommendation: Graceful degradation):
    If reset fails:
    1. Backup is restored so users see OLD data (no downtime)
    2. user_actions_loaded is set to True (users can use old data)
    3. system_reset_failed flag is set to True (indicates issue to frontend)
    4. Developer is alerted via email/g-chat to investigate
    5. System will retry reset on next trimester start date
    
    This approach prioritizes user experience over having latest data:
    - Users see old data rather than loading message/downtime
    - Developers have time to investigate without time pressure
    - No cascade failures or partial state corruption
    
    Process mimics init_minimal_data() + background_load_user_actions():
    - Backs up current state before starting
    - Sets user_actions_loaded to False during reset (shows loading state)
    - Reloads all mappings and data structures
    - Sets user_actions_loaded to True when complete
    - Updates last_refresh_date to current date
    
    Execution time: ~30 minutes (similar to app startup)
    """
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping, user_actions_loaded, last_refresh_date
    global system_reset_failed, system_reset_failure_reason
    
    logger.info("=" * 80)
    logger.info("TRIMESTER START DETECTED - INITIATING FULL SYSTEM RESET")
    logger.info("=" * 80)
    
    # Step 0: Backup current state before attempting reset
    # Recommendation: This allows graceful fallback if any step fails
    logger.info("Step 0/4: Backing up current system state...")
    _backup_current_state()
    logger.info("Current system state backed up successfully | function: full_system_reset")
    
    # Set loading flag to False to prevent users from accessing incomplete data
    # Recommendation: Keep user_actions_loaded=False during reset so users see maintenance message
    user_actions_loaded = False
    logger.info(f"User actions loading flag set to False | function: full_system_reset")
    
    try:
        # Step 1: Reload category-to-ID mapping (discovers new courses)
        logger.info("Step 1/4: Reloading course category mappings (Query #107)...")
        df_map_category_to_id = load_df_map_category_to_id()
        logger.info(f"Course mappings reloaded | courses: {len(df_map_category_to_id)} | function: full_system_reset")
        
        # Step 2: Reload user ID-username mapping (discovers new users)
        logger.info("Step 2/4: Reloading user ID mappings (Query #108)...")
        id_username_mapping = load_id_username_mapping()
        logger.info(f"User mappings reloaded | users: {len(id_username_mapping)} | function: full_system_reset")
        
        # Step 3: Rebuild all user actions data from scratch (Query #103, #102 for all trimesters)
        logger.info("Step 3/4: Rebuilding all user actions data from scratch...")
        user_actions_dictionaries = load_user_actions_dictionaries()
        logger.info(f"User actions data rebuilt | trimesters: {list(user_actions_dictionaries.keys())} | function: full_system_reset")
        
        # Step 4: Update refresh date to today
        logger.info("Step 4/4: Finalizing reset...")
        last_refresh_date = datetime.now().strftime("%d-%m-%Y")
        logger.info(f"Last refresh date updated | date: {last_refresh_date} | function: full_system_reset")
        
        # Set loading flag to True - system ready for use
        user_actions_loaded = True
        system_reset_failed = False
        system_reset_failure_reason = None
        logger.info(f"User actions loading flag set to True | function: full_system_reset")
        
        logger.info("=" * 80)
        logger.info("FULL SYSTEM RESET COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
    except Exception as e:
        # Recommendation: On failure, restore backup and allow users to access old data
        # This provides graceful degradation instead of complete system downtime
        logger.error(f"FULL SYSTEM RESET FAILED | error: {str(e)} | function: full_system_reset", exc_info=True)
        
        # Step 1: Restore data from backup
        logger.warning("Restoring previous system state from backup...")
        _restore_from_backup()
        
        # Step 2: Allow users to access old data (don't leave system in loading state)
        logger.warning("Setting user_actions_loaded=True to allow access to old data...")
        user_actions_loaded = True
        
        # Step 3: Set failure flags for alerting and monitoring
        system_reset_failed = True
        system_reset_failure_reason = str(e)
        logger.warning(f"system_reset_failed flag set to True | reason: {system_reset_failure_reason}")
        
        # Step 4: Alert developer to investigate
        logger.warning("Alerting development team about reset failure...")
        _alert_developer_of_reset_failure(system_reset_failure_reason)
        
        logger.error("=" * 80)
        logger.error("FULL SYSTEM RESET FAILED - FALLBACK TO OLD DATA")
        logger.error(f"Reason: {system_reset_failure_reason}")
        logger.error("Users will see previous trimester data while developers investigate")
        logger.error("System will attempt reset again on next trimester start date")
        logger.error("=" * 80)


# DATA REFRESH FUNCTION
def refresh_all_data():
    """
    Perform incremental daily data refresh (delta updates).
    
    This function runs at 3:15 AM on all days EXCEPT trimester start dates.
    Safety check: If accidentally triggered on a trimester start date, it exits early.
    
    On regular days:
    - Fetches only NEW user actions since last_refresh_date (Query #103, #102)
    - Merges with existing data and removes duplicates
    - Recalculates metrics and scores for updated datasets
    - Updates last_refresh_date to current date
    
    Trimester handling:
    - Removes oldest trimester (4 trimesters back) from memory
    - Initializes new trimester structures if detected
    """
    # Safety check: Skip incremental refresh on trimester start dates
    # Recommendation: Prevent overlap between full reset and incremental refresh jobs
    if is_trimester_start_today():
        logger.warning("Trimester start date detected - skipping incremental refresh (full system reset should run instead)")
        logger.warning("function: refresh_all_data | action: SKIPPED")
        return
    
    global user_actions_dictionaries, df_map_category_to_id, id_username_mapping, last_refresh_date
    today = datetime.now().strftime("%d-%m-%Y")
    trimester_corresponding_to_today = get_current_trimester()
    trimester_data_to_be_removed = get_previous_trimesters(trimester_corresponding_to_today)[3]
    user_actions_dictionaries.pop(trimester_data_to_be_removed, None)
    logger.info(f"Refresh started | function: refresh_all_data | today: {today} | terms: {list(user_actions_dictionaries.keys())}")

    # SAFETY NET: Initialize new trimester if missing (fallback if full_system_reset failed or edge cases)
    # This ensures incremental data collection can start even if trimester reset didn't succeed
    if trimester_corresponding_to_today not in user_actions_dictionaries:
        logger.info(f"New trimester detected | function: refresh_all_data | trimester: {trimester_corresponding_to_today}")
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
            logger.warning(f"Category not found | function: refresh_all_data | date: {today} | course: {category_name} | term: {trimester_corresponding_to_today}")
            continue
        query_params_for_103 = {"category_id": str(category_id), "start_date": last_refresh_date, "end_date": today}

        latest_user_actions_df = execute_discourse_query(103, query_params=query_params_for_103)
        logger.info(f"Course data fetched | function: refresh_all_data | date: {today} | course: {category_name} | rows: {len(latest_user_actions_df)}")
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
    logger.info(f"Data refresh completed | function: refresh_all_data | term: {trimester_corresponding_to_today} | last_refresh_date: {last_refresh_date}")
