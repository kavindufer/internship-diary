import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta

REQUIRED_COLUMNS = ['Task Name', 'Start Date', 'Due Date', 'Assignee', 'Linked Entity']

def load_schedule(csv_file):
    df = pd.read_csv(csv_file)

    # Clean and normalize columns
    df.columns = [col.strip() for col in df.columns]

    # Ensure required columns exist
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Convert date columns to datetime
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['Start Date', 'Due Date'])

    # Sort for readability
    df = df.sort_values(by='Start Date').reset_index(drop=True)

    return df


def get_weekly_task_groups(df, internship_start_date, exclude_weekends=True, leave_dates=[]):
    if isinstance(internship_start_date, pd.Timestamp):
        internship_start_date = internship_start_date.date()

    # Start at beginning of the week
    current = internship_start_date - timedelta(days=internship_start_date.weekday())
    end = df['Due Date'].max().date()

    weeks = {}

    while current <= end:
        week_start = current
        week_end = week_start + timedelta(days=6)

        mask = (df['Start Date'].dt.date <= week_end) & (df['Due Date'].dt.date >= week_start)
        week_df = df[mask]

        tasks = defaultdict(list)
        for _, row in week_df.iterrows():
            task_start = max(row['Start Date'].date(), week_start)
            task_end = min(row['Due Date'].date(), week_end)
            for i in range((task_end - task_start).days + 1):
                day = task_start + timedelta(days=i)
                if exclude_weekends and day.weekday() >= 5:
                    continue
                if day in leave_dates:
                    continue
                task_text = f"{row['Task Name']} ({row['Linked Entity']})" if pd.notna(row['Linked Entity']) else row['Task Name']
                tasks[day].append(task_text)

        # Always include all weekdays for the week, even if no tasks
        full_week = {}
        for i in range(5):
            day = week_start + timedelta(days=i)
            if exclude_weekends and day.weekday() >= 5:
                continue
            if day in leave_dates:
                continue
            full_week[day] = tasks.get(day, [])

        label = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        weeks[label] = full_week

        current += timedelta(days=7)

    return weeks
