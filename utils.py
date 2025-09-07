import re
from datetime import date

def sanitize_filepath(name):
    # Replace invalid characters with underscore
    return re.sub(r'[<>:"/\\|?* ]', '_', name)

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