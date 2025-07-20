import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.csv_parser import load_schedule, get_weekly_task_groups

st.set_page_config(page_title="Internship Diary Automator", layout="centered")

st.title("📅 Internship Diary Automator")
st.write("Start by uploading your task schedule to generate weekly reports.")

csv_file = st.file_uploader("📄 Upload Task Schedule CSV", type=["csv"])

if csv_file:
    try:
        df = load_schedule(csv_file)
        st.success("✅ CSV successfully parsed!")

        st.subheader("🔍 Task Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.info(f"📅 Earliest Task: {df['Start Date'].min().date()} — Latest Task: {df['Due Date'].max().date()}")

        # === Internship Start Date
        st.subheader("📅 Internship Start Date")
        csv_earliest_start = df['Start Date'].min().date()
        start_date_input = st.date_input("When did your internship start?", value=csv_earliest_start)

        # === Leave Input
        st.subheader("🛌 Leaves Taken")
        num_leaves = st.number_input("How many leave days did you take?", min_value=0, step=1)
        leave_dates = []
        leave_data = {}

        for i in range(num_leaves):
            col1, col2 = st.columns([1, 3])
            with col1:
                leave_day = st.date_input(f"Leave {i + 1} - Date", key=f"leave_date_{i}")
            with col2:
                leave_reason = st.text_input(f"Leave {i + 1} - Reason", key=f"leave_reason_{i}")
            if leave_day:
                leave_dates.append(leave_day)
                leave_data[leave_day] = leave_reason

        # === Weekly Grouping
        st.subheader("📆 Weekly Grouping")

        # -- FIX: group weeks from earliest date (internship or task), not only by internship start
        grouping_anchor = min(start_date_input, csv_earliest_start)
        weekly_tasks = get_weekly_task_groups(
            df,
            grouping_anchor=grouping_anchor,
            exclude_weekends=True,
            leave_dates=leave_dates
        )
        week_labels = sorted(list(weekly_tasks.keys()))

        if week_labels:
            selected_week = st.selectbox("Select a week to view tasks", week_labels)

            if selected_week:
                tasks = weekly_tasks[selected_week]
                st.markdown(f"### 📋 Tasks for {selected_week}")

                week_start = datetime.strptime(selected_week.split(" to ")[0], "%Y-%m-%d").date()
                for i in range(5):  # Weekdays only
                    day = week_start + timedelta(days=i)
                    st.markdown(f"**{day.strftime('%A')} ({day.strftime('%Y-%m-%d')}):**")

                    if day in leave_dates:
                        reason = leave_data.get(day, "No reason provided")
                        st.warning(f"🛌 Leave taken — {reason}")
                        if not tasks.get(day):
                            st.info("_No tasks on this day (on leave)_")
                    elif not tasks.get(day):
                        st.write("_No tasks_")
                    else:
                        for task in tasks[day]:
                            st.write(f"- {task}")
        else:
            st.warning("⚠️ No weeks found in your task data range.")

    except Exception as e:
        st.error(f"❌ Failed to parse CSV: {e}")
else:
    st.warning("📂 Please upload a CSV file to proceed.")
