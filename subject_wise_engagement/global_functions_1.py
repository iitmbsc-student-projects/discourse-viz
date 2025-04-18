import re
def sanitize_filepath(name):
    # Replace invalid characters with underscore
    return re.sub(r'[<>:"/\\|?* ]', '_', name)
