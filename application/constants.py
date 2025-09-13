import os

# env = "dev"
env = "production"

# Discourse related constants
api_key = os.environ.get('API_KEY')
API_KEY = api_key

api_headers = {
                "Api-Key": api_key,
                "Api-Username": "shubhamg"
           }
DISCOURSE_BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
GROUP_NAME = "discourse_analytics"
API_USERNAME = 'shubhamG'


# COURSES LIST

foundation_courses = ['Mathematics for Data Science I','Statistics for Data Science I','Computational Thinking','English I','English II','Mathematics for Data Science II','Statistics for Data Science II','Programming in Python']
diploma_programming_courses = ['Programming, Data Structures and Algorithms','Database Management Systems','Modern Application Development I','System Commands','Modern Application Development II','Programming Concepts using Java']
diploma_data_science_courses = ['Machine Learning Foundations','Business Data Management','Machine Learning Techniques','Machine Learning Practice','Tools in Data Science','Business Analytics']
degree_courses = ['Deep Learning','AI: Search Methods for Problem Solving','Software Testing','Software Engineering','Strategies for Professional Growth','Industry 4.0','Design Thinking for Data Driven App Development','Speech Technology','Privacy & Security in Online Social Media','Algorithmic Thinking in Bioinformatics','Data Visualization Design','Linear Statistical Models','Market Research','Introduction to Big Data','Financial Forensics','Big Data and Biological Networks','Advanced Algorithms','Special topics in ML (Reinforcement Learning)','Statistical Computing','Programming in C','Mathematical Thinking','Computer System Design','Operating Systems','Deep Learning for Computer Vision','Large Language Models','Managerial Economics','Game Theory and Strategy','Corporate Finance','Deep Learning Practice','Introduction to Natural Language Processing', "Algorithms for Data Science (ADS)","Generative AI", "MLOPS"]

degree_courses.sort()
diploma_data_science_courses.sort()
diploma_programming_courses.sort()
foundation_courses.sort()

# DICTIONARIES FOR user-actions-df analysis
action_to_description = {
"1": "likes_given",
"2": "likes_received",
"3": "bookmarked_post",
"4": "created_new_topic",
"5": "replied",
"6": "received_response",
"7": "user_was_mentioned",
"9": "user's_post_quoted",
"11": "user_edited_post",
"12": "user_sent_private_message",
"13": "recieved_a_private_message",
"15": "solved_a_topic",
"16": "user_was_assigned",
"17": "linked"
}


weights_dict_for_course_specific_engagement = { 'likes_given': 0.3, # 0.3
                "likes_received": 0.8, # changed from 0.7
                "created_new_topic": 0.5, # changed from 1.0
                "replied": 0.7,
                'solved_a_topic': 10 # Highest weight
            }

weights_dict_for_overall_engagement = { 'likes_given': 0.4, # likes_given is also important
                "likes_received": 0.8,
                "topics_created": 0.4,
                "posts_created": 0.7,
                "days_visited": 0.3, # decreased weightage because it is a very common action
                'solutions': 10,
}