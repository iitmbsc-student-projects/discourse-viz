# %%
import requests
import pandas as pd
import os
import time
import json

from global_functions_1 import execute_query_108

df_userid_name_map = execute_query_108(query_id=108,query_params=None) # No query params is required because we need data of all users