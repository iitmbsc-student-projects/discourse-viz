
import requests
import pandas as pd
import os
import time
import json  # Importing json to handle JSON data

from global_functions_1 import execute_query_102

params = {"start_date":"01/01/2025","end_date":'30/04/2025'}
req_data = execute_query_102(query_id=102,query_params=params)



