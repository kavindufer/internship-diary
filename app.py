from dotenv import load_dotenv
load_dotenv()
import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.csv_parser import load_schedule, get_weekly_task_groups
from utils.openai_helper import get_task_question
from utils.docx_handler import fill_report_template  # Make sure this exists

st.set_page_config(page_title="Internship Diary Automator", layout="centered")

st.title("📅 Internship Diary Automator")
st.write("Start by uploading your task schedule to generate weekly reports.")

# -- Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found in environment variable OPENAI_API_KEY.")
    st.stop()

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

                # === Get unique tasks for the week (skip leaves)
                unique_tasks = set()
                for i in range(5):  # Monday to Friday
                    day = week_start + timedelta(days=i)
                    if day in leave_dates:
                        continue
                    day_tasks = tasks.get(day, [])
                    for task in day_tasks:
                        unique_tasks.add(task)

                # === CHAT-STYLE Q&A SECTION
                if 'chat_task_list' not in st.session_state or st.session_state.get('chat_week') != selected_week:
                    st.session_state['chat_task_list'] = sorted(list(unique_tasks))
                    st.session_state['chat_current'] = 0
                    st.session_state['chat_answers'] = {}
                    st.session_state['chat_questions'] = {}
                    st.session_state['chat_week'] = selected_week

                task_list = st.session_state['chat_task_list']
                idx = st.session_state['chat_current']
                answers = st.session_state['chat_answers']
                questions = st.session_state['chat_questions']

                if idx < len(task_list):
                    current_task = task_list[idx]
                    # Get question from OpenAI (cache it)
                    if current_task not in questions:
                        with st.spinner("AI is thinking..."):
                            q = get_task_question(current_task, OPENAI_API_KEY)
                        questions[current_task] = q
                        st.session_state['chat_questions'] = questions

                    st.markdown(f"**AI:** {questions[current_task]}")
                    user_answer = st.text_area("Your answer:", key=f"answer_{current_task[:16]}")

                    col_next, col_skip = st.columns([3, 1])
                    with col_next:
                        if st.button("Next"):
                            answers[current_task] = user_answer
                            st.session_state['chat_answers'] = answers
                            st.session_state['chat_current'] += 1
                            st.rerun()
                    with col_skip:
                        if st.button("Skip"):
                            st.session_state['chat_current'] += 1
                            st.rerun()

                else:
                    st.success("All tasks answered! Review below and make any edits you like:")
                    for task in task_list:
                        new_answer = st.text_area(
                            f"Edit entry for {task}:",
                            value=answers.get(task, ""),
                            key=f"review_{task[:16]}"
                        )
                        st.session_state['chat_answers'][task] = new_answer
                    st.info("Your edits are saved live. You can now generate and download your weekly report.")

                    # === GENERATE DOCX BUTTON
                    if st.button("Generate Weekly Report"):
                        template_path = "templates/Daily Report Template.docx"
                        week_label = selected_week
                        output_dir = "outputs"
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                        week_start = datetime.strptime(selected_week.split(" to ")[0], "%Y-%m-%d").date()
                        output_filename = f"Diary_{week_label.replace(' ', '').replace(':', '-')}.docx"
                        output_path = os.path.join(output_dir, output_filename)

                        fill_report_template(
                            template_path,
                            output_path,
                            week_label,
                            st.session_state['chat_answers'],
                            week_start
                        )
                        with open(output_path, "rb") as f:
                            st.success("Your weekly report is ready!")
                            st.download_button("Download Report", f, file_name=output_filename)

        else:
            st.warning("⚠️ No weeks found in your task data range.")

    except Exception as e:
        st.error(f"❌ Failed to parse CSV: {e}")
else:
    st.warning("📂 Please upload a CSV file to proceed.")
