import streamlit as st
from datetime import datetime, timedelta
import os

from utils.csv_parser import load_schedule, get_weeks_range, get_tasks_for_week
from utils.docx_handler import load_template, fill_weekly_report, save_report

# ---- Constants ----
TEMPLATE_PATH = "templates/report_template.docx"
OUTPUT_DIR = "output"

# ---- Streamlit Setup ----
st.set_page_config(page_title="Intern Weekly Report Generator", layout="centered")
st.title("📅 Intern Weekly Report Generator")

# ---- Sidebar Upload ----
st.sidebar.header("Upload Task Schedule")
csv_file = st.sidebar.file_uploader("📄 Upload your CSV file", type=["csv"])

# ---- Main App Logic ----
if csv_file:
    # Load CSV and get week ranges
    df = load_schedule(csv_file)
    min_date, max_date = df["Start Date"].min().date(), df["Due Date"].max().date()
    week_ranges = get_weeks_range(min_date, max_date)

    # Week selector
    st.subheader("📆 Select a Week to Generate Report")
    week_options = [f"{start} to {end}" for start, end in week_ranges]
    selected_week_str = st.selectbox("Choose Week:", week_options)
    week_start = datetime.strptime(selected_week_str.split(" to ")[0], "%Y-%m-%d")

    # Show weekly tasks
    st.subheader("🗂️ Tasks This Week")
    daily_tasks = get_tasks_for_week(df, week_start)

    for i in range(7):
        day = week_start + timedelta(days=i)
        task_list = daily_tasks.get(day, ["No task"])
        st.markdown(f"**{day.strftime('%A')} ({day}):**")
        for task in task_list:
            st.write(f"- {task}")

    # Generate report
    if st.button("📤 Generate Weekly Report"):
        doc = load_template(TEMPLATE_PATH)
        filled_doc = fill_weekly_report(doc, week_start, daily_tasks)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"Weekly_Report_{week_start}.docx")
        save_report(filled_doc, output_path)

        with open(output_path, "rb") as f:
            st.success("✅ Report generated successfully!")
            st.download_button(
                label="⬇️ Download Weekly Report",
                data=f,
                file_name=os.path.basename(output_path),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

else:
    st.info("📂 Please upload a CSV file to begin.")
