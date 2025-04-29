# %% [markdown]
# # This notebook creates some basic visualizations of the data for whole discourse. The data is NOT related to any specific category.

# %%
import altair as alt
import pandas as pd
import numpy as np
import os
import IPython.display

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

