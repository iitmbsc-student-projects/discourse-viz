
def get_all_data_dicts():
    import pandas as pd
    import numpy as np
    import time

    # Imports from other programs
    from subject_wise_engagement.global_functions_1 import sanitize_filepath, get_current_trimester, get_previous_trimesters,get_course_specific_dataframes, get_overall_engagement_df, get_top_10_first_responders
    from subject_wise_engagement.fetch_category_IDs_107 import df_map_category_to_id

    curr_plus_prev_trimesters = get_previous_trimesters(get_current_trimester())[:2] # The items of this list will act as keys of the dictionary; elements are terms in descending order, like current(t2-2025), previous(t1-2025), t3-2024 and so on # CHANGED FOR TESTING

    def get_trimester_dates(trimester): # THIS WILL HELP IN SENDING DATES AS PARAMS FOR QUERIES LIKE 103
        t, y = trimester.split('-')
        trimester_dates = {
            't1': ('01/01', '30/04'),
            't2': ('01/05', '31/08'),
            't3': ('01/09', '31/12')
        }
        return (f"{trimester_dates[t][0]}/{y}",f"{trimester_dates[t][1]}/{y}")
    
    user_actions_dictionaries = {}
    error_list = []

    for term in curr_plus_prev_trimesters: # keys are actually the terms, like "t1-2025","t3-2024"; # THIS LOOP IS FOR FINDING THE REQUIRED DATA FOR COURSES
        key=term
        user_actions_dictionaries[key] = {}
        try:
            for row in df_map_category_to_id.itertuples(): # This loop is for finding course-specific dataframes for each term
                try:
                    category_id = row.category_id
                    if not (category_id==26): continue # REMOVE FROM FINAL DEPLOYMENT # CHANGED FOR TESTING
                    category_name = sanitize_filepath(row.name).lower() # Removes characters like :," " etc and replaces them with "_"
                    if category_name not in user_actions_dictionaries[key]:
                        user_actions_dictionaries[key][category_name] = {}
                        user_actions_dictionaries[key][category_name]["user_actions_df"] = pd.DataFrame() # This will be used to create week-wise engagement graph
                        user_actions_dictionaries[key][category_name]["raw_metrics"] = pd.DataFrame()
                        user_actions_dictionaries[key][category_name]["unnormalized_scores"] = pd.DataFrame()
                        user_actions_dictionaries[key][category_name]["log_normalized_scores"] = pd.DataFrame()
                    
                    start_date, end_date = get_trimester_dates(term)
                    params = {"category_id": str(category_id), "start_date": start_date, "end_date": end_date}
                    
                    start = time.time()
                    user_actions_df, raw_metrics_df, unnormalized_scores_df, log_normalized_scores_df = get_course_specific_dataframes(query_params=tuple(params.items()))
                    end = time.time()
                    """with open("time_log.txt", "a") as f: # REMOVE FROM DEPLOYMENT
                        print(f"get_course_specific_dataframes | course={category_name} | term={term}: {round(end - start,2)} seconds\n")
                        f.write(f"get_course_specific_dataframes | course={category_name} | term={term}: {round(end - start,2)} seconds\n")"""

                    # if not user_actions_df.empty and len(user_actions_df)>75: # THIS WILL BE IMPLEMENTED LATER AFTER DISCUSSION
                    user_actions_dictionaries[key][category_name]["user_actions_df"] = user_actions_df
                        
                    user_actions_dictionaries[key][category_name]["raw_metrics"] = raw_metrics_df # So now we have the raw metrics for each category for each term.

                    user_actions_dictionaries[key][category_name]["unnormalized_scores"] = unnormalized_scores_df

                    user_actions_dictionaries[key][category_name]["log_normalized_scores"] = log_normalized_scores_df

                except Exception as exec:
                    print(f"Error: {exec} for subject: {category_name} for term: {term}")
                    error_list.append((key,category_name,exec))
                    continue
        except Exception as exec:
            print(f"Error: {exec} for term: {term}")
            error_list.append(term)
            continue


    for term in curr_plus_prev_trimesters:
        # THIS LOOP IS FOR FINDIND THE REQUIRED DATA OF OVERALL DISCOURSE
        start_date, end_date = get_trimester_dates(term)
        params = {"start_date": start_date, "end_date": end_date}
        
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
            print(f"Error: {exec} for term: {term}")
            error_list.append(term)
            continue
    
    if error_list: print(error_list)
    return user_actions_dictionaries # MOST IMP VARIABLE IN THE WHOLE CODE

if __name__=="__main__":
    user_actions_dictionaries = get_all_data_dicts()