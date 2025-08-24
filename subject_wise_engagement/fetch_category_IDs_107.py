# # This notebook was created to get the category IDs for the categories/courses that we want to analyse. For example, mlp<-->33

import requests
import pandas as pd
import time, os
import json  # Importing json to handle JSON data
from functools import lru_cache 
from subject_wise_engagement.execute_query import execute_query_107
# from execute_query import execute_query_107


start = time.time()
df_map_category_to_id = execute_query_107(query_id=107,query_params=None)
irrelevant_categories = [63,64,79,80,86,87,88,91,95,96,97,103,104,105,106,107,112,113,114]
df_map_category_to_id = df_map_category_to_id[~df_map_category_to_id["category_id"].isin(irrelevant_categories)]
df_map_category_to_id.to_csv("category_id_name_mapping.csv", index=False)
end = time.time()
if __name__ == "__main__":
    print(df_map_category_to_id.head())