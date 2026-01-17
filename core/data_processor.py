
def get_all_data_dicts():
    import pandas as pd
    import numpy as np

    # Imports from other programs
    from core.utils import sanitize_filepath, get_current_trimester, get_previous_trimesters, get_trimester_dates
    from processors.course_data_processors import get_course_specific_dataframes
    from processors.overall_discourseData_processors import get_overall_engagement_df
    from application.constants import env
    from core.logging_config import get_logger
    
    from core.data_loader import get_df_map_category_to_id
    
    logger = get_logger("core.data_loader")
    df_map_category_to_id = get_df_map_category_to_id()

    curr_plus_prev_trimesters = get_previous_trimesters(get_current_trimester())[:3] # The items of this list will act as keys of the dictionary; elements are terms in descending order, like current(t2-2025), previous(t1-2025), t3-2024 and so on # CHANGED FOR TESTING

    
    
    user_actions_dictionaries = {}
    error_list = []

    for term in curr_plus_prev_trimesters: # keys are actually the terms, like "t1-2025","t3-2024"; # THIS LOOP IS FOR FINDING THE REQUIRED DATA FOR COURSES
        key=term
        user_actions_dictionaries[key] = {}
        try:
            for row in df_map_category_to_id.itertuples(): # This loop is for finding course-specific dataframes for each term
                try:
                    category_id = row.category_id
                    if env == "dev":
                        if not (category_id==18): continue
                    category_name = sanitize_filepath(row.name).lower() # Removes characters like :," " etc and replaces them with "_"
                    if category_name not in user_actions_dictionaries[key]:
                        user_actions_dictionaries[key][category_name] = {}
                        user_actions_dictionaries[key][category_name]["user_actions_df"] = pd.DataFrame() # This will be used to create week-wise engagement graph
                        user_actions_dictionaries[key][category_name]["raw_metrics"] = pd.DataFrame()
                        user_actions_dictionaries[key][category_name]["unnormalized_scores"] = pd.DataFrame()
                        user_actions_dictionaries[key][category_name]["log_normalized_scores"] = pd.DataFrame()
                    
                    start_date, end_date = get_trimester_dates(term)
                    params = {"category_id": str(category_id), "start_date": start_date, "end_date": end_date}
                    
                    user_actions_df, raw_metrics_df, unnormalized_scores_df, log_normalized_scores_df = get_course_specific_dataframes(query_params=tuple(params.items()))

                    # if not user_actions_df.empty and len(user_actions_df)>75: # THIS WILL BE IMPLEMENTED LATER AFTER DISCUSSION
                    user_actions_dictionaries[key][category_name]["user_actions_df"] = user_actions_df
                        
                    user_actions_dictionaries[key][category_name]["raw_metrics"] = raw_metrics_df # So now we have the raw metrics for each category for each term.

                    user_actions_dictionaries[key][category_name]["unnormalized_scores"] = unnormalized_scores_df

                    user_actions_dictionaries[key][category_name]["log_normalized_scores"] = log_normalized_scores_df

                except Exception as exec:
                    logger.error(f"Error processing course data | function: get_all_data_dicts | course: {category_name} | term: {term} | error: {exec}", extra={"course": category_name, "term": term}, exc_info=True)
                    error_list.append((key,category_name,exec))
                    continue
        except Exception as exec:
            logger.error(f"Error processing term data | function: get_all_data_dicts | term: {term} | error: {exec}", extra={"term": term}, exc_info=True)
            error_list.append(term)
            continue


    for term in curr_plus_prev_trimesters:
        # THIS LOOP IS FOR FINDIND THE REQUIRED DATA OF OVERALL DISCOURSE
        start_date, end_date = get_trimester_dates(term)
        params = {"start_date": start_date, "end_date": end_date, "domain":"ds.study.iitm.ac.in"}
        
        user_actions_dictionaries[term]["overall"] = {
            "raw_metrics": pd.DataFrame(),
            "unnormalized_scores": pd.DataFrame(),
            "log_normalized_scores": pd.DataFrame()
        }
        try:
            raw_metrics_all_users_df, unnormalized_scores_all_users_df, log_normalized_scores_all_users_df = get_overall_engagement_df(query_params=tuple(params.items()))

            user_actions_dictionaries[term]["overall"]["raw_metrics"] = raw_metrics_all_users_df
            user_actions_dictionaries[term]["overall"]["unnormalized_scores"] = unnormalized_scores_all_users_df
            user_actions_dictionaries[term]["overall"]["log_normalized_scores"] = log_normalized_scores_all_users_df
        except Exception as exec:
            logger.error("Error processing overall engagement data", extra={"term": term}, exc_info=True)
            error_list.append(term)
            continue
    
    if error_list:
        logger.warning("Data loading completed with errors", extra={"error_count": len(error_list), "errors": str(error_list)[:500]})
    else:
        logger.info("Data loading completed successfully", extra={"terms": list(user_actions_dictionaries.keys())})
    return user_actions_dictionaries # MOST IMP VARIABLE IN THE WHOLE CODE

if __name__=="__main__":
    user_actions_dictionaries = get_all_data_dicts()
