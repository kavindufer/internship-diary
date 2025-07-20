from dotenv import load_dotenv
load_dotenv()
import os
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from utils.csv_parser import load_schedule, get_weekly_task_groups
from utils.openai_helper import (
    get_task_question, get_notes_summary, refine_task_description, get_daywise_partials
)
from utils.docx_handler import fill_report_template

st.set_page_config(page_title="Internship Diary Automator", layout="centered")
st.title("📅 Internship Diary Automator")
st.write("Start by uploading your task schedule to generate weekly reports.")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found in environment variable OPENAI_API_KEY.")
    st.stop()

st.sidebar.header("Report Setup")
training_mode = st.sidebar.selectbox(
    "Select Training Mode", ["Online", "Physical", "Hybrid"]
)
your_signature_file = st.sidebar.file_uploader("Your signature (PNG)", type=["png"], key="your_sig")
supervisor_designation = st.sidebar.text_input("Supervisor Designation")
supervisor_signature_file = st.sidebar.file_uploader("Supervisor signature (PNG)", type=["png"], key="sup_sig")

your_signature_path, supervisor_signature_path = None, None
if your_signature_file:
    your_signature_path = f"temp_yoursig_{your_signature_file.name}"
    with open(your_signature_path, "wb") as f:
        f.write(your_signature_file.getbuffer())
if supervisor_signature_file:
    supervisor_signature_path = f"temp_supsig_{supervisor_signature_file.name}"
    with open(supervisor_signature_path, "wb") as f:
        f.write(supervisor_signature_file.getbuffer())

csv_file = st.file_uploader("📄 Upload Task Schedule CSV", type=["csv"])

task_json_path = "task_descriptions.json"
if os.path.exists(task_json_path):
    with open(task_json_path, "r") as f:
        task_json = json.load(f)
else:
    task_json = {}

def save_task_json():
    with open(task_json_path, "w") as f:
        json.dump(task_json, f, indent=2)

def update_task_history(task_json, task_name, new_full_desc, start_date, end_date):
    entry = task_json.setdefault(task_name, {"history": [], "daywise_descriptions": {}})
    # Only add new if it's a new description or new range
    found = False
    for seg in entry["history"]:
        if seg["description"] == new_full_desc and seg["start"] == start_date and seg["end"] == end_date:
            found = True
            break
    if not found:
        entry["history"].append({"start": start_date, "end": end_date, "description": new_full_desc})
    task_json[task_name] = entry

def get_history_for_task(task_name):
    return task_json.get(task_name, {}).get("history", [])

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
                week_ending = (week_start + timedelta(days=6)).strftime('%Y-%m-%d')
                days_of_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

                # Build mapping: {task_name: [dates]}
                unique_tasks = {}
                for i in range(7):
                    day = week_start + timedelta(days=i)
                    if day in leave_dates:
                        continue
                    for task in tasks.get(day, []):
                        unique_tasks.setdefault(task, []).append(day.strftime('%Y-%m-%d'))

                # --- CHAT Q&A, AI-refine and show immediately ---
                if 'chat_task_list' not in st.session_state or st.session_state.get('chat_week') != selected_week:
                    st.session_state['chat_task_list'] = list(unique_tasks.keys())
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
                    if user_answer:
                        refined_answer = refine_task_description(user_answer, OPENAI_API_KEY)
                        st.info("**AI-refined:** " + refined_answer)
                        if st.button("Use this answer and continue"):
                            answers[current_task] = refined_answer
                            st.session_state['chat_answers'] = answers
                            st.session_state['chat_current'] += 1
                            st.rerun()
                        if st.button("Edit again"):
                            pass  # Stay on this task for further editing
                else:
                    st.success("All tasks answered! Review below and make any edits you like:")
                    for task in task_list:
                        new_answer = st.text_area(
                            f"Edit entry for {task}:",
                            value=answers.get(task, ""),
                            key=f"review_{task[:16]}"
                        )
                        if st.button(f"Refine {task}"):
                            new_answer = refine_task_description(new_answer, OPENAI_API_KEY)
                        st.session_state['chat_answers'][task] = new_answer

                    # Save/extend task history and create partials for each day
                    for task, days in unique_tasks.items():
                        full_desc = st.session_state['chat_answers'].get(task, "")
                        if not full_desc:
                            continue
                        start_date = days[0]
                        end_date = days[-1]
                        entry = task_json.setdefault(task, {"history": [], "daywise_descriptions": {}})
                        # Only append if new segment (i.e., if description or date range changed)
                        need_new = True
                        for seg in entry["history"]:
                            if seg["start"] == start_date and seg["end"] == end_date and seg["description"] == full_desc:
                                need_new = False
                                break
                        if need_new:
                            entry["history"].append({"start": start_date, "end": end_date, "description": full_desc})
                        # Now make sure daywise_partials exist for all days
                        missing_days = [d for d in days if d not in entry["daywise_descriptions"]]
                        if missing_days:
                            partials = get_daywise_partials(entry["history"], missing_days, OPENAI_API_KEY)
                            for d in missing_days:
                                entry["daywise_descriptions"][d] = partials[d]
                        task_json[task] = entry
                    save_task_json()

                    # --- Show days spanned, days left ---
                    for task in task_list:
                        all_days = sorted(set(task_json.get(task, {}).get("daywise_descriptions", {}).keys()))
                        week_days = unique_tasks[task]
                        # Find which week_days are new and which are already filled
                        new_days = [d for d in week_days if d not in all_days]
                        done_days = [d for d in week_days if d in all_days]

                        st.markdown(f"#### 📝 {task}")
                        st.write(f"**Covers {len(all_days)} days:**")
                        st.markdown(
                            " ".join(
                                [f"`{d}`" if d in done_days else f"<span style='background-color: #FFE066; padding:2px 6px; border-radius:4px'>{d}</span>" for d in week_days]
                            ),
                            unsafe_allow_html=True,
                        )
                        st.write(f"**New this week:** {' '.join(new_days) if new_days else '*No new days in this week!*'}")

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
                                # For each task on this day, use the correct partial (history aware)
                                day_tasks = tasks.get(d, [])
                                parts = []
                                for task in day_tasks:
                                    daywise = task_json.get(task, {}).get("daywise_descriptions", {})
                                    partial = daywise.get(date_str, "")
                                    if partial:
                                        parts.append(f"{task}:\n{partial}")
                                desc = "\n\n".join(parts)
                            daily_entries[day_name] = {"date": date_str, "desc": desc}

                        fill_report_template(
                            template_path,
                            output_path,
                            week_ending=week_ending,
                            training_mode=training_mode,
                            daily_entries=daily_entries,
                            details_notes=details_notes,
                            your_signature_path=your_signature_path,
                            supervisor_signature_path=supervisor_signature_path,
                            supervisor_designation=supervisor_designation
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
