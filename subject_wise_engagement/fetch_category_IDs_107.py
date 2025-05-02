# # This notebook was created to get the category IDs for the categories/courses that we want to analyse. For example, mlp<-->33

import requests
import pandas as pd
import time, os
import json  # Importing json to handle JSON data
from functools import lru_cache 
from subject_wise_engagement.execute_query import execute_query_107
# from execute_query import execute_query_107



df_map_category_to_id = execute_query_107(query_id=107,query_params=None)

irrelevant_categories = """Course LxIs
Math for Electronics I
Electronic Systems Thinking and Circuits
Basic Digital Systems
Electrical and Electronic Circuits
Embedded C Programming
Math for Electronics II
Signals and Systems
Analog Electronic Systems
Digital Signal Processing
Control Engineering
Digital System Design
Sensors and Application
Electronics Lab
Introduction to Linux Shell
electromagnetic_fields_and_transmission_lines
electronic_product_design"""
irrelevant_categories = irrelevant_categories.replace("\n",",").split(",")
# Remove rows where "name" column doesn't have any of the irrelevant categories
df_map_category_to_id = df_map_category_to_id[~df_map_category_to_id["name"].isin(irrelevant_categories)]