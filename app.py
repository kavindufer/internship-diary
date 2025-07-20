from dotenv import load_dotenv
load_dotenv()
import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.csv_parser import load_schedule, get_weekly_task_groups
from utils.openai_helper import get_task_question, get_notes_summary
from utils.docx_handler import fill_report_template

st.set_page_config(page_title="Internship Diary Automator", layout="centered")

st.title("📅 Internship Diary Automator")
st.write("Start by uploading your task schedule to generate weekly reports.")

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found in environment variable OPENAI_API_KEY.")
    st.stop()

# --- Extra Info: Training Mode, Designation, Signature PNG
st.sidebar.header("Report Setup")
training_mode = st.sidebar.selectbox(
    "Select Training Mode", ["Online", "Physical", "Hybrid"]
)
designation = st.sidebar.text_input("Your Designation")
signature_file = st.sidebar.file_uploader("Upload your signature (PNG)", type=["png"])
signature_path = None
if signature_file:
    signature_path = f"temp_signature_{signature_file.name}"
    with open(signature_path, "wb") as f:
        f.write(signature_file.getbuffer())

csv_file = st.file_uploader("📄 Upload Task Schedule CSV", type=["csv"])

def task_assigned_on_day(task, day, tasks_by_day):
    return day in tasks_by_day and task in tasks_by_day[day]

if csv_file:
    try:
        df = load_schedule(csv_file)
        st.success("✅ CSV successfully parsed!")

        st.subheader("🔍 Task Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.info(f"📅 Earliest Task: {df['Start Date'].min().date()} — Latest Task: {df['Due Date'].max().date()}")

        st.subheader("📅 Internship Start Date")
        csv_earliest_start = df['Start Date'].min().date()
        start_date_input = st.date_input("When did your internship start?", value=csv_earliest_start)

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
                days_of_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

                unique_tasks = set()
                for i in range(7):
                    day = week_start + timedelta(days=i)
                    if day in leave_dates:
                        continue
                    day_tasks = tasks.get(day, [])
                    for task in day_tasks:
                        unique_tasks.add(task)

                # --- CHAT Q&A SECTION ---
                if 'chat_task_list' not in st.session_state or st.session_state.get('chat_week') != selected_week:
                    st.session_state['chat_task_list'] = sorted(list(unique_tasks))
                    st.session_state['chat_current'] = 0
                    st.session_state['chat_answers'] = {}
                    st.session_state['chat_questions'] = {}
                    st.session_state['chat_week'] = selected_week
                    st.session_state.pop("auto_details_notes", None)
                    st.session_state.pop("auto_notes_week", None)

                task_list = st.session_state['chat_task_list']
                idx = st.session_state['chat_current']
                answers = st.session_state['chat_answers']
                questions = st.session_state['chat_questions']

                if idx < len(task_list):
                    current_task = task_list[idx]
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

                    # --- Auto-Summarize Details/Notes ---
                    if "auto_details_notes" not in st.session_state or st.session_state.get('auto_notes_week') != selected_week:
                        if st.button("Auto-generate Weekly Details/Notes"):
                            all_entries = "\n".join([
                                f"{task}: {ans}" for task, ans in st.session_state['chat_answers'].items()
                            ])
                            summary = get_notes_summary(all_entries, OPENAI_API_KEY)
                            st.session_state["auto_details_notes"] = summary
                            st.session_state["auto_notes_week"] = selected_week

                    details_notes = st.text_area(
                        "Enter your weekly details/notes, problems, etc.",
                        value=st.session_state.get("auto_details_notes", ""),
                        key="details_notes"
                    )

                    st.info("Your edits are saved live. You can now generate and download your weekly report.")

                    if st.button("Generate Weekly Report"):
                        template_path = "templates/Daily Report Template.docx"
                        week_label = selected_week
                        output_dir = "outputs"
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                        week_start = datetime.strptime(selected_week.split(" to ")[0], "%Y-%m-%d").date()
                        week_ending = (week_start + timedelta(days=6)).strftime('%Y-%m-%d')
                        output_filename = f"Diary_{week_label.replace(' ', '').replace(':', '-')}.docx"
                        output_path = os.path.join(output_dir, output_filename)

                        daily_entries = {}
                        for i, day_name in enumerate(days_of_week):
                            d = week_start + timedelta(days=i)
                            date_str = d.strftime('%Y-%m-%d')
                            desc = ""
                            if d in leave_dates:
                                desc = f"Leave taken — {leave_data.get(d, 'No reason provided')}"
                            else:
                                day_tasks = tasks.get(d, [])
                                if day_tasks:
                                    desc = "\n\n".join([
                                        f"{task}:\n{st.session_state['chat_answers'].get(task, '')}"
                                        for task in day_tasks
                                    ])
                            daily_entries[day_name] = {"date": date_str, "desc": desc}

                        fill_report_template(
                            template_path,
                            output_path,
                            week_ending=week_ending,
                            training_mode=training_mode,
                            daily_entries=daily_entries,
                            details_notes=details_notes,
                            designation=designation,
                            signature_path=signature_path
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
