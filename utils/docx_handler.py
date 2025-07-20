from docx import Document
from datetime import timedelta

def load_template(template_path):
    return Document(template_path)

def fill_weekly_report(doc, week_start, tasks_by_day):
    week_end = week_start + timedelta(days=6)

    # --- Table 1: Daily breakdown ---
    main_table = doc.tables[0]

    # Fill header row with week ending date
    main_table.cell(0, 1).text = f"FOR THE WEEK ENDING\nSunday: {week_end.strftime('%Y-%m-%d')}"

    # Fill daily entries (rows 2–8)
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_date = day.date()
        task_text = "\n".join(tasks_by_day.get(day_date, [])) or "No task"

        main_table.cell(i + 2, 1).text = day_date.strftime('%Y-%m-%d')
        main_table.cell(i + 2, 2).text = task_text

    return doc

def save_report(doc, output_path):
    doc.save(output_path)
