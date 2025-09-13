import re
from datetime import date, datetime, timedelta

def sanitize_filepath(name):
    # Replace invalid characters with underscore
    return re.sub(r'[<>:"/\\|?* ]', '_', name)

def get_trimester_dates(trimester): # THIS WILL HELP IN SENDING DATES AS PARAMS FOR QUERIES LIKE 103
        t, y = trimester.split('-')
        trimester_dates = {
            't1': ('01-01', '30/04'),
            't2': ('01-05', '31-08'),
            't3': ('01-09', '31-12')
        }
        return (f"{trimester_dates[t][0]}-{y}",f"{trimester_dates[t][1]}-{y}")

def get_current_trimester():
    today = date.today()
    year = today.year
    month = today.month

    if 1 <= month <= 4:
        trimester = 't1'
    elif 5 <= month <= 8:
        trimester = 't2'
    else:
        trimester = 't3'

    return f"{trimester}-{year}" # e.g "t2-2025"

def get_trimester_week(date_str):
    """
    Given a date string in 'YYYY-MM-DD', returns:
    (trimester_number, week_in_trimester, week_start_date, week_end_date)
    
    Week start and end dates are in format 'dd-mm-yyyy'.
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    year = date.year

    # Define trimester start dates
    t1_start = datetime(year, 1, 1)
    t2_start = datetime(year, 5, 1)
    t3_start = datetime(year, 9, 1)

    if date < t2_start:
        trimester = 1
        trimester_start = t1_start
    elif date < t3_start:
        trimester = 2
        trimester_start = t2_start
    else:
        trimester = 3
        trimester_start = t3_start

    days_diff = (date - trimester_start).days
    week_in_trimester = days_diff // 7 + 1  # 1-based week number

    # Calculate week start and end dates
    week_start = trimester_start + timedelta(weeks=week_in_trimester - 1)
    week_end = week_start + timedelta(days=6)

    # Format the dates as 'dd-mm-yyyy'
    week_start_str = week_start.strftime("%d-%m-%Y")
    week_end_str = week_end.strftime("%d-%m-%Y")

    return f"t{trimester}-w{week_in_trimester};  ({week_start_str}, {week_end_str})"

def get_previous_trimesters(current_trimester):
    trimesters = ['t1', 't2', 't3']
    t, y = current_trimester.split('-')
    year = int(y)
    index = trimesters.index(t)

    result = []
    for _ in range(3):
        index -= 1
        if index < 0:
            index = 2
            year -= 1
        result.append(f"{trimesters[index]}-{year}")
    
    return [current_trimester]+result # ['t2-2025', 't1-2025', 't3-2024', 't2-2024']