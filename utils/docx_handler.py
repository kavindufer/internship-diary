from docx import Document
from docx.shared import Inches

def fill_report_template(
    template_path,
    output_path,
    week_ending,
    training_mode,
    daily_entries,
    details_notes,
    your_signature_path=None,
    supervisor_signature_path=None,
    supervisor_designation=None
):
    doc = Document(template_path)

    # --- Table 0 ---
    diary_table = doc.tables[0]
    # Week ending
    orig_text = diary_table.cell(0,0).text
    prefix = orig_text.split("\n")[0] if "\n" in orig_text else orig_text
    diary_table.cell(0,0).text = f"{prefix}\nSunday: {week_ending}"
    # Training mode
    diary_table.cell(0,3).text = f"TRAINING MODE\n{training_mode}"

    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    for i, day in enumerate(days):
        row = diary_table.rows[i+2]
        row.cells[1].text = daily_entries.get(day, {}).get("date", "")
        row.cells[2].text = daily_entries.get(day, {}).get("desc", "")

    # --- Table 1 ---
    details_table = doc.tables[1]
    details_table.cell(1,0).text = details_notes

    # Your signature at [2,2]
    if your_signature_path:
        details_table.cell(2,2).text = ""
        paragraph = details_table.cell(2,2).paragraphs[0]
        run = paragraph.add_run()
        run.add_picture(your_signature_path, width=Inches(1.2))

    # Supervisor signature and designation at [5,1]
    sig_text = "DESIGNATION AND SIGNATURE"
    if supervisor_designation:
        sig_text += f"\n{supervisor_designation}"
    details_table.cell(5,1).text = sig_text
    if supervisor_signature_path:
        paragraph = details_table.cell(5,1).add_paragraph()
        run = paragraph.add_run()
        run.add_picture(supervisor_signature_path, width=Inches(1.2))

    # Week-ending date at [5,0]
    details_table.cell(5,0).text = f"DATE: {week_ending}"

    doc.save(output_path)
