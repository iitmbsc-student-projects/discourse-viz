# PURPOSE: This notebook creates some basic visualizations of the data for whole discourse. The data is NOT related to any specific category.
# MODIFICATIONS NEEDED: The function "create_weekwise_engagement(df)" from global_functions_1.py should be placed here

import altair as alt
import pandas as pd
import numpy as np
import os
import IPython.display

from core.utils import get_trimester_week
from application.constants import action_to_description

def create_stacked_bar_chart_for_overall_engagement(raw_metrics, term):
    # Define the metrics we are interested in
    metrics = ['likes_received', 'likes_given', 'days_visited', 'solutions',
               "topics_created","posts_created"] # 'topics_viewed', 'posts_read' removed

    # Ensure 'username' is included when filtering
    filtered_metrics = raw_metrics.set_index(['user_id', 'username'])[metrics].loc[:, (raw_metrics[metrics] != 0).any()]

    # Transform data to long format
    long_df = filtered_metrics.reset_index().melt(id_vars=["user_id", "username"], var_name="metric", value_name="count")


    if not long_df.empty:
        # Create the Altair stacked bar chart
        chart = alt.Chart(long_df).mark_bar().encode(
            x=alt.X("count:Q", title="Total User Interactions", 
                    axis=alt.Axis(format="~s", titleFontSize=14)),  # Formatting x-axis ticks
            y=alt.Y("username:N", title="Username", sort="-x", 
                    axis=alt.Axis(titleFontSize=14)),  # Changed from user_id to username
            color=alt.Color("metric:N", title="Activity Type"),
            tooltip=["username", "metric", "count"]  # Changed tooltip from user_id to username
        ).properties(
            title=f"Most Active Users for ({term})",
            width=600,
            height=400
        )
        return chart
    else:
        print("<h2>No non-zero metrics to display.<h2>")

def create_empty_chart():
    text="""Course was either not offered this term OR it had extremely less interactions on discourse"""
    # Create a dummy dataframe with a single row
    df = pd.DataFrame({'x': [0], 'y': [0], 'text': [text]})

    # Create the chart
    chart = alt.Chart(df).mark_text(
        align='center',
        baseline='middle',
        fontSize=18,
        color='gray'
    ).encode(
        x=alt.value(250),  # X position in pixels
        y=alt.value(150),  # Y position in pixels
        text='text:N'
    ).properties(
        width=500,
        height=300
    )

    return chart

def create_stacked_bar_chart_for_course_specific_engagement(raw_metrics, subject):
    # Assuming raw_metrics is already loaded
    metrics = ['created_new_topic', 'likes_given', 'likes_received', 'replied', 'solved_a_topic']
    # Only use metrics that exist in the DataFrame
    metrics = [m for m in metrics if m in raw_metrics.columns]
    

    # Filter out metrics where all users have value 0
    filtered_metrics = raw_metrics.set_index('acting_username')[metrics].loc[:, (raw_metrics[metrics] != 0).any()]

    if not filtered_metrics.empty:
        # Convert to long format for Altair
        raw_metrics_long = raw_metrics.melt(id_vars=['acting_username'], 
                                            value_vars=metrics, 
                                            var_name='Activity Type', 
                                            value_name='Count')

        # Create Altair stacked bar chart
        chart = alt.Chart(raw_metrics_long).mark_bar().encode(
            x=alt.X('Count:Q', title="Total User Interactions",
                    axis=alt.Axis(titleFontSize=14)),
            y=alt.Y('acting_username:N', title="Username", sort='-x',
                    axis=alt.Axis(titleFontSize=14)),
            color=alt.Color('Activity Type:N', title="Activity Type"),
            tooltip=['acting_username', 'Activity Type', 'Count']
        ).properties(
            title=f'Most Active Users ({subject})',
            width=600,
            height=400
        ).configure_legend(
            orient='right'
        )
        return chart

    else:
        return("<h2>No non-zero metrics to display.</h2>")
    
def create_empty_chart_in_case_of_errors(message = """There was some error generating chart. Please contact the support team if issue persists"""):
    text = message
    # Create a dummy dataframe with a single row
    df = pd.DataFrame({'x': [0], 'y': [0], 'text': [text]})

    # Create the chart
    chart = alt.Chart(df).mark_text(
        align='center',
        baseline='middle',
        fontSize=18,
        color='gray'
    ).encode(
        x=alt.value(250),  # X position in pixels
        y=alt.value(150),  # Y position in pixels
        text='text:N'
    ).properties(
        width=500,
        height=300
    )

    return chart

def create_weekwise_engagement(user_actions_df):
    """
    This function creates a weekwise engagement dataframe.
    It takes the user_actions_df as input and returns the weekwise engagement dataframe.
    The weekwise engagement dataframe is created by grouping the user_actions_df by week_number and then counting the number of actions for each week.
    """
    user_actions_df["created_at"] = user_actions_df["created_at"].map(lambda x: x.split("T")[0]) # Convert datetime to date string
    user_actions_df["week_number"] = user_actions_df["created_at"].map(lambda x: get_trimester_week(x)) # Get trimester week for each date, for example "t1-w1;  (01-01-2025, 07-01-2025)"


    user_actions_df["action_name_new"] = user_actions_df["action_type"].astype(str).map(action_to_description)
    df2 = user_actions_df[["week_number", "action_name_new"]] # Keep only the week_number and action_name_new columns

    # Create a pivot table
    pivot_table = pd.pivot_table(
        df2,
        index="week_number",  # Rows
        columns="action_name_new",  # Columns
        aggfunc="size",  # Count occurrences
        fill_value=0  # Fill missing values with 0
    )
    # Remove the specified columns from the pivot table
    columns_to_be_removed = ["user_edited_post", "likes_received", "linked", "received_response", "user's_post_quoted", "user_was_mentioned", "user_edited_post"]
    pivot_table = pivot_table.drop(columns=columns_to_be_removed, errors='ignore')
    pivot_table["total_score"] = pivot_table.apply(lambda row: sum(row[col] for col in pivot_table.columns), axis=1)

    # Reset the index of the pivot_table to make "week_number" a column
    pivot_table_reset = pivot_table.reset_index()

    # Sort by total_score in descending order
    pivot_table_reset = pivot_table_reset.sort_values(by="total_score", ascending=False)

    # Combine all metric details into a single string for display in the tooltip
    pivot_table_reset["metrics_details"] = pivot_table_reset.apply(
        lambda row: "\n".join([f"{col}:{row[col]} | " for col in pivot_table.columns if col != "total_score"]),
        axis=1
    )
    # Create the heatmap
    heatmap = alt.Chart(pivot_table_reset).mark_rect().encode(
        x=alt.X(
            'week_number:O', 
            title='Week Number (start:end)', 
            sort=pivot_table_reset["week_number"].tolist(),
            axis=alt.Axis(labelAngle=45)  # Set label angle here
        ),
        y=alt.Y('total_score:Q', title='Total Score'),
        color=alt.value('#2E86AB'),
        tooltip=[
            alt.Tooltip('week_number:O', title='Week Number'),
            alt.Tooltip('total_score:Q', title='Total Score'),
            alt.Tooltip('metrics_details:N', title='Metrics Details')
        ]
    ).properties(
        width=700,
        # height=400,
        title="Histogram of Total Score by Week Number"
    )

    return heatmap