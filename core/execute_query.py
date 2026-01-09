import time, requests, json
import pandas as pd
from application.constants import env, API_USERNAME, GROUP_NAME, DISCOURSE_BASE_URL, API_KEY


def execute_discourse_query(query_id, query_params=None):
    match query_id:
        case 103: print("Executing query_103 for course-specific user actions | params:", query_params)
        case 102: print("Executing query_102 for overall discourse engagement | params:", query_params)
        case 107: print("Executing query_107 FOR FETCHING CATEGORY_IDS")
        case 108: print("Executing query_108 for userid-name mapping")
        case _: raise ValueError("INVALID DISCOURSE QUERY-ID")
    
    iteration_count = 0  # Initialize iteration counter
    results_list = []  # List to store results
    has_more_results = True  # Flag to control the loop for pagination

    # Check if query_params is provided
    if query_params is None:
        pass  # No parameters provided, continue with default
    else:
        if not isinstance(query_params, dict): # Ensure query_params is a dictionary
            raise ValueError("Query parameters must be a dictionary.")

    # Set up headers for the API request
    headers = {
        "Accept": "*/*",
        "Api-Key": API_KEY,  # Get API key from userdata
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
            # Check for specific 429 error in the exception message
            if "429" in str(e) and "Too Many Requests" in str(e):
                raise RuntimeError(f"**********\nStopping execution due to rate limiting\nERROR: {e} for query_id = {query_id}\nQUERY_PARAMS = {query_params}\n**********")
            else:
                # Log other exceptions
                print(f"**********\nStopping execution due to\nERROR: {e} for query_id = {query_id}\nQUERY_PARAMS = {query_params}\n**********")


        iteration_count += 1  # Increment iteration count for pagination
        if env=="dev": 
            if iteration_count>0: break # REMOVE FROM FINAL DEPLOYMENT
        time.sleep(1.03)  # Wait before the next request

    results_dataframe = pd.DataFrame(results_list)  # Convert results list to DataFrame
    return results_dataframe  # Return the DataFrame with results


if __name__ == "__main__":
    from datetime import datetime
    x = datetime.now().strftime("%d-%m-%Y")
    print(x)
    query_params_for_103 = {"category_id": str(26), "start_date": x, "end_date": "15/09/2025"}
    print(len(execute_discourse_query(103, query_params={})))