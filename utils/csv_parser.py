import pandas as pd
from datetime import datetime, timedelta

def load_schedule(csv_path):
    df = pd.read_csv(csv_path)
    df['Start Date'] = pd.to_datetime(df['Start Date'])
    df['Due Date'] = pd.to_datetime(df['Due Date'])
    return df

def get_weeks_range(start_datetime, end_datetime):
    """Return all Monday-to-Sunday week tuples (datetime objects)"""
    weeks = []
    current = start_datetime
    while current <= end_datetime:
        week_start = current - timedelta(days=current.weekday())
        week_end = week_start + timedelta(days=6)
        weeks.append((week_start, week_end))
        current += timedelta(days=7)
    return weeks

def get_tasks_for_week(df, week_start):
    """Return a dictionary of daily tasks for a given week"""
    week_end = week_start + timedelta(days=6)

    mask = (df['Start Date'] <= week_end) & (df['Due Date'] >= week_start)
    week_tasks = df[mask]

    daily_tasks = {}
    for _, row in week_tasks.iterrows():
        start = max(row['Start Date'], week_start)
        end = min(row['Due Date'], week_end)

        for n in range((end - start).days + 1):
            day = (start + timedelta(days=n)).date()  # Use .date() as key
            entry = f"{row['Task Name']} ({row['Linked Entity']})" if pd.notna(row['Linked Entity']) else row['Task Name']
            if day not in daily_tasks:
                daily_tasks[day] = []
            daily_tasks[day].append(entry)

    return daily_tasks
