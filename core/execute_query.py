import time, requests, json
import logging
import pandas as pd
from application.constants import env, API_USERNAME, GROUP_NAME, DISCOURSE_BASE_URL, API_KEY
from core.logging_config import get_logger
from core.utils import _alert_developer_of_reset_failure


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
            logger.debug(f"Fetching page {iteration_count} | params: {query_params}", extra={"query_id": query_id, "page": iteration_count})
            response = requests.request("POST", request_url, data=data_payload, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            json_response = response.json()  # Parse the JSON response

            # Check if there are no results
            if json_response["result_count"] == 0:
                logger.warning(f"Query returned zero results | function: execute_discourse_query | query_id: {query_id} | params_provided: {query_params} | page: {iteration_count}", extra={"query_id": query_id, "page": iteration_count})
                has_more_results = False  # No more results to fetch
                break

            # Iterate over the rows in the response
            for index in range(len(json_response['rows'])):
                # Append each row as a dictionary to the results list
                results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))

        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, "status_code", None)
            if status_code == 429:
                # Retry with increasing delay for rate limiting
                max_retries = 5
                for retry_attempt in range(max_retries):
                    delay = 3 * (retry_attempt + 1)  # 3s, 6s, 9s, 12s, 15s
                    logger.warning(
                        f"Rate limited (429), retrying after {delay}s (attempt {retry_attempt + 1}/{max_retries})",
                        extra={
                            "query_id": query_id,
                            "page": iteration_count,
                            "retry_attempt": retry_attempt + 1,
                            "delay_seconds": delay,
                        },
                    )
                    time.sleep(delay)
                    
                    try:
                        response = requests.request("POST", request_url, data=data_payload, headers=headers)
                        response.raise_for_status()
                        json_response = response.json()
                        
                        if json_response["result_count"] == 0:
                            logger.warning("Query returned zero results", extra={"query_id": query_id, "page": iteration_count})
                            has_more_results = False
                            break
                        
                        for index in range(len(json_response['rows'])):
                            results_list.append(dict(zip(json_response['columns'], json_response['rows'][index])))
                        
                        break  # Success, exit retry loop
                        
                    except requests.exceptions.HTTPError as retry_error:
                        if getattr(retry_error.response, "status_code", None) == 429:
                            if retry_attempt == max_retries - 1:
                                # Max retries reached
                                logger.error(
                                    f"Rate limited (429) after {max_retries} retries",
                                    extra={
                                        "query_id": query_id,
                                        "page": iteration_count,
                                        "params_provided": bool(query_params),
                                    },
                                    exc_info=True,
                                )
                                raise RuntimeError(
                                    f"**********\nStopping execution due to persistent rate limiting\nERROR: {retry_error} for query_id = {query_id}\nQUERY_PARAMS = {query_params}\nMax retries ({max_retries}) exceeded\n**********"
                                ) from retry_error
                            else:
                                continue  # Try again
                        else:
                            # Different HTTP error during retry
                            raise
            else: # HTTP errors other than 429
                logger.exception(
                    f"HTTP error while executing query | function: execute_discourse_query | query_id: {query_id} | params_provided: {query_params}",
                    extra={
                        "query_id": query_id,
                        "page": iteration_count,
                        "params_provided": bool(query_params),
                        "status_code": status_code,
                    },
                )
                has_more_results = False  # Stop pagination on non-429 errors
        except requests.exceptions.RequestException as e:
            # Non-HTTP request errors (connection, timeout, etc.)
            logger.exception(
                f"Request error while executing query | function: execute_discourse_query | query_id: {query_id} | params_provided: {query_params} | page: {iteration_count}",
                extra={"query_id": query_id, "page": iteration_count, "params_provided": bool(query_params)},
            )
            has_more_results = False  # Stop pagination after request failure
            break
        except Exception as e:
            # Log other unexpected exceptions
            logger.exception(
                f"Unexpected error while executing query | function: execute_discourse_query | query_id: {query_id} | params_provided: {query_params} | page: {iteration_count}",
                extra={"query_id": query_id, "page": iteration_count, "params_provided": bool(query_params)},
            )
            has_more_results = False
            break


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