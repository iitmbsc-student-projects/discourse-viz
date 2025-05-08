from functools import lru_cache
import time, requests, json, os
import pandas as pd
# import winsound

def execute_query_103(query_id, query_params=None): # for course-specific user actions
    print("Now inside query 103") # REMOVE
    DISCOURSE_BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
    GROUP_NAME = "discourse_analytics"
    API_KEY_GLOBAL= os.environ.get('API_KEY')
    API_USERNAME = 'shubhamG'

    iteration_count = 0  # Initialize iteration counter
    results_list = []  # List to store results
    has_more_results = True  # Flag to control the loop for pagination

    # Check if query_params is provided
    if query_params is None:
        pass  # No parameters provided, continue with default
    else:
        # Ensure query_params is a dictionary
        if not isinstance(query_params, dict):
            raise ValueError("Query parameters must be a dictionary.")

    # Set up headers for the API request
    headers = {
        "Accept": "*/*",
        "Api-Key": API_KEY_GLOBAL,  # Get API key from userdata
        "Api-Username": API_USERNAME,  # Set the username for the API
        "Content-Type": "multipart/form-data"  # Set content type
    }

    # Loop until there are no more results
    while has_more_results:
        # Construct the request URL for the API
        request_url = f"{DISCOURSE_BASE_URL}/g/{GROUP_NAME}/reports/{query_id}/run"

        # Prepare the data payload for the request
        if query_params is not None:
            payload = {'page': str(iteration_count)}  # Add page number to payload
            payload.update(query_params)  # Update payload with additional query parameters
            data_payload = 'params=' + json.dumps(payload)  # Convert payload to JSON string
        else:
            data_payload = f'params={{"page": "{iteration_count}"}}'  # Default payload with page number

        try:
            # Send POST request to the API
            response = requests.request("POST", request_url, data=data_payload, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            json_response = response.json()  # Parse the JSON response

            # Check if there are no results
            if json_response["result_count"] == 0:
                has_more_results = False  # No more results to fetch
                break

            # Iterate over the rows in the response
            for index in range(len(json_response['rows'])):
                # Append each row as a dictionary to the results list
                results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))

        except Exception as e:
            # winsound.Beep(frequency=1000, duration=500)
            # Check for specific 429 error in the exception message
            if "429" in str(e) and "Too Many Requests" in str(e):
                raise RuntimeError(f"Stopping execution due to rate limiting: {e} for query_params = {query_params} inside 103")
            else:
                # Log other exceptions
                print(f'error: {e}')


        iteration_count += 1  # Increment iteration count for pagination
        # if iteration_count>2: break # REMOVE
        time.sleep(2)  # Wait before the next request

    results_dataframe = pd.DataFrame(results_list)  # Convert results list to DataFrame
    return results_dataframe  # Return the DataFrame with results


@lru_cache(maxsize=None, typed=False)
def execute_query_107(query_id, query_params=None): # fetch category_ids
    print("RIGHT NOW INSIDE QUERY 107 FOR FETCHING CATEGORY_IDS")
    DISCOURSE_BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
    GROUP_NAME = "discourse_analytics"
    API_KEY_GLOBAL= os.environ.get('API_KEY')
    API_USERNAME = 'shubhamG'

    iteration_count = 0  # Initialize iteration counter
    results_list = []  # List to store results
    has_more_results = True  # Flag to control the loop for pagination

    # Check if query_params is provided
    if query_params is None:
        pass  # No parameters provided, continue with default
    else:
        # Ensure query_params is a dictionary
        if not isinstance(query_params, dict):
            raise ValueError("Query parameters must be a dictionary.")

    # Set up headers for the API request
    headers = {
        "Accept": "*/*",
        "Api-Key": API_KEY_GLOBAL,  # Get API key from userdata
        "Api-Username": "shubhamG",  # Set the username for the API
        "Content-Type": "multipart/form-data"  # Set content type
    }

    # Loop until there are no more results
    while has_more_results:
        # Construct the request URL for the API
        request_url = f"{DISCOURSE_BASE_URL}/g/{GROUP_NAME}/reports/{query_id}/run"

        # Prepare the data payload for the request
        if query_params is not None:
            payload = {'page': str(iteration_count)}  # Add page number to payload
            payload.update(query_params)  # Update payload with additional query parameters
            data_payload = 'params=' + json.dumps(payload)  # Convert payload to JSON string
        else:
            data_payload = f'params={{"page": "{iteration_count}"}}'  # Default payload with page number

        try:
            # Send POST request to the API
            print(data_payload)
            response = requests.request("POST", request_url, data=data_payload, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            json_response = response.json()  # Parse the JSON response

            # Check if there are no results
            if json_response["result_count"] == 0:
                has_more_results = False  # No more results to fetch
                break

            # Iterate over the rows in the response
            for index in range(len(json_response['rows'])):
                # Append each row as a dictionary to the results list
                results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))

        except requests.exceptions.RequestException as e:
            # winsound.Beep(frequency=1000, duration=500)
            # Log request-related errors
            # logging.error(f'Request error: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'Status code: {e.response.status_code}')  # Log status code
                print(f'Error text: {e.response.text}')  # Log error text

            has_more_results = False  # Stop fetching results
            break
        except ValueError as e:
            # Log JSON parsing errors
            print(f'Error parsing JSON: {e}')
            has_more_results = False  # Stop fetching results
            break
        except KeyError as e:
            # Log key-related errors
            print(f'Key error: {e}')
            has_more_results = False  # Stop fetching results
            break

        iteration_count += 1  # Increment iteration count for pagination
        time.sleep(2)  # Wait before the next request

    results_dataframe = pd.DataFrame(results_list)  # Convert results list to DataFrame
    return results_dataframe  # Return the DataFrame with results

@lru_cache(maxsize=None, typed=False)
def execute_query_108(query_id, query_params=None): # userid-name mapping
    print("Now inside execute_query_108 for userid-name mapping")
    DISCOURSE_BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
    GROUP_NAME = "discourse_analytics"
    API_KEY_GLOBAL= os.environ.get('API_KEY')
    API_USERNAME = 'shubhamG'

    iteration_count = 0  # Initialize iteration counter
    results_list = []  # List to store results
    has_more_results = True  # Flag to control the loop for pagination

    # Check if query_params is provided
    if query_params is None:
        pass  # No parameters provided, continue with default
    else:
        # Ensure query_params is a dictionary
        if not isinstance(query_params, dict):
            raise ValueError("Query parameters must be a dictionary.")

    # Set up headers for the API request
    headers = {
        "Accept": "*/*",
        "Api-Key": API_KEY_GLOBAL,  # Get API key from userdata
        "Api-Username": API_USERNAME,  # Set the username for the API
        "Content-Type": "multipart/form-data"  # Set content type
    }

    # Loop until there are no more results
    while has_more_results:
        # Construct the request URL for the API
        request_url = f"{DISCOURSE_BASE_URL}/g/{GROUP_NAME}/reports/{query_id}/run"

        # Prepare the data payload for the request
        if query_params is not None:
            payload = {'page': str(iteration_count)}  # Add page number to payload
            payload.update(query_params)  # Update payload with additional query parameters
            data_payload = 'params=' + json.dumps(payload)  # Convert payload to JSON string
        else:
            data_payload = f'params={{"page": "{iteration_count}"}}'  # Default payload with page number

        try:
            # Send POST request to the API
            # print(data_payload)
            response = requests.request("POST", request_url, data=data_payload, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            json_response = response.json()  # Parse the JSON response

            # Check if there are no results
            if json_response["result_count"] == 0:
                has_more_results = False  # No more results to fetch
                break

            # Iterate over the rows in the response
            for index in range(len(json_response['rows'])):
                # Append each row as a dictionary to the results list
                results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))

        except Exception as e:
            # winsound.Beep(frequency=1000, duration=500)
            # Log key-related errors
            print(f'EXCEPTION: {e}')
            has_more_results = False  # Stop fetching results
            break

        iteration_count += 1  # Increment iteration count for pagination
        time.sleep(2)  # Wait before the next request

    results_dataframe = pd.DataFrame(results_list)  # Convert results list to DataFrame
    return results_dataframe  # Return the DataFrame with results


def execute_query_102(query_id, query_params=None): # overall discourse engagement
    print(f"Now inside query 102 overall discourse engagement FOR PARAMS = {query_params}") # REMOVE
    DISCOURSE_BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
    GROUP_NAME = "discourse_analytics"
    API_KEY_GLOBAL= os.environ.get('API_KEY')
    API_USERNAME = 'shubhamG'

    iteration_count = 0  # Initialize iteration counter
    results_list = []  # List to store results
    has_more_results = True  # Flag to control the loop for pagination

    # Check if query_params is provided
    if query_params is None:
        pass  # No parameters provided, continue with default
    else:
        # Ensure query_params is a dictionary
        if not isinstance(query_params, dict):
            raise ValueError("Query parameters must be a dictionary.")

    # Set up headers for the API request
    headers = {
        "Accept": "*/*",
        "Api-Key": API_KEY_GLOBAL,  # Get API key from userdata
        "Api-Username": "shubhamG",  # Set the username for the API
        "Content-Type": "multipart/form-data"  # Set content type
    }
    # Loop until there are no more results
    while has_more_results:
        # Construct the request URL for the API
        request_url = f"{DISCOURSE_BASE_URL}/g/{GROUP_NAME}/reports/{query_id}/run"

        # Prepare the data payload for the request
        if query_params is not None:
            payload = {'page': str(iteration_count)}  # Add page number to payload
            payload.update(query_params)  # Update payload with additional query parameters
            data_payload = 'params=' + json.dumps(payload)  # Convert payload to JSON string
        else:
            data_payload = f'params={{"page": "{iteration_count}"}}'  # Default payload with page number

        try:
            # Send POST request to the API
            print(data_payload)
            response = requests.request("POST", request_url, data=data_payload, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            json_response = response.json()  # Parse the JSON response

            # Check if there are no results
            if json_response["result_count"] == 0:
                has_more_results = False  # No more results to fetch
                break

            # Iterate over the rows in the response
            for index in range(len(json_response['rows'])):
                # Append each row as a dictionary to the results list
                results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))

        except Exception as e:
            # winsound.Beep(frequency=1000, duration=500)
            has_more_results = False  # Stop fetching results
            print(f"Error: {e}")
            break

        iteration_count += 1  # Increment iteration count for pagination
        if iteration_count>2: break
        time.sleep(2)  # Wait before the next request

    results_dataframe = pd.DataFrame(results_list)  # Convert results list to DataFrame
    return results_dataframe  # Return the DataFrame with results
