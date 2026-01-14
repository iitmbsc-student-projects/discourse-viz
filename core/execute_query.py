import time, requests, json
import logging
import pandas as pd
from application.constants import env, API_USERNAME, GROUP_NAME, DISCOURSE_BASE_URL, API_KEY
from core.logging_config import get_logger


def execute_discourse_query(query_id, query_params=None):
    logger_map = {
        102: get_logger("query.102"),
        103: get_logger("query.103"),
        107: get_logger("query.107"),
        108: get_logger("query.108"),
    }
    logger = logger_map.get(query_id, get_logger("query"))

    match query_id:
        case 103: logger.info("Executing query_103 for course-specific user actions", extra={"params_provided": bool(query_params)})
        case 102: logger.info("Executing query_102 for overall discourse engagement", extra={"params_provided": bool(query_params)})
        case 107: logger.info("Executing query_107 for fetching category IDs")
        case 108: logger.info("Executing query_108 for userid-name mapping")
        case _: raise ValueError("INVALID DISCOURSE QUERY-ID")
    
    iteration_count = 0  # Initialize iteration counter
    results_list = []  # List to store results
    has_more_results = True  # Flag to control the loop for pagination
    start_time = time.perf_counter()

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
            logger.debug("Fetching page", extra={"query_id": query_id, "page": iteration_count})
            response = requests.request("POST", request_url, data=data_payload, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            json_response = response.json()  # Parse the JSON response

            # Check if there are no results
            if json_response["result_count"] == 0:
                logger.warning("Query returned zero results", extra={"query_id": query_id, "page": iteration_count})
                has_more_results = False  # No more results to fetch
                break

            # Iterate over the rows in the response
            for index in range(len(json_response['rows'])):
                # Append each row as a dictionary to the results list
                results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))

        except Exception as e:
            # Check for specific 429 error in the exception message
            if "429" in str(e) and "Too Many Requests" in str(e):
                logger.error(
                    "Rate limited (429) while executing query",
                    extra={"query_id": query_id, "page": iteration_count, "params_provided": bool(query_params)},
                    exc_info=True,
                )
                raise RuntimeError(
                    f"**********\nStopping execution due to rate limiting\nERROR: {e} for query_id = {query_id}\nQUERY_PARAMS = {query_params}\n**********"
                )
            else:
                # Log other exceptions
                logger.exception(
                    "Error while executing query",
                    extra={"query_id": query_id, "page": iteration_count, "params_provided": bool(query_params)},
                )


        iteration_count += 1  # Increment iteration count for pagination
        if env=="dev": 
            if iteration_count>0: break
        time.sleep(1.2)  # Wait before the next request

    results_dataframe = pd.DataFrame(results_list)  # Convert results list to DataFrame
    duration = time.perf_counter() - start_time
    logger.info(
        "Completed query",
        extra={
            "query_id": query_id,
            "rows": len(results_dataframe),
            "pages": iteration_count + 1,
            "duration_sec": round(duration, 2),
        },
    )
    return results_dataframe  # Return the DataFrame with results