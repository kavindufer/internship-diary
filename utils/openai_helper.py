import openai

def get_task_question(task_name, api_key):
    client = openai.OpenAI(api_key=api_key)
    prompt = (
        f"You are helping an intern write a daily diary. "
        f"Generate a friendly, specific question to help the intern describe their work on the following task:\n"
        f"Task: {task_name}\n"
        "Make it conversational and encourage them to mention details, challenges, and learnings."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=60,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

def refine_task_description(raw_text, api_key):
    client = openai.OpenAI(api_key=api_key)
    prompt = (
        "Please correct the grammar and spelling of the following text. "
        "Do not change the style, add, or remove any content. "
        "Return only the fixed text.\n\n"
        f"Text:\n{raw_text}"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=400,
        temperature=0,
    )
    return response.choices[0].message.content.strip()

def get_notes_summary(all_entries, api_key):
    client = openai.OpenAI(api_key=api_key)
    prompt = (
        "Below are my rough diary notes for this week. "
        "Please combine them into a single, natural paragraph or two, written in the first person (as 'I'), "
        "correcting any grammar and spelling mistakes but keeping my voice and style. "
        "Don't summarize in third person or add information, just rewrite my notes as me, fluently and clearly.\n\n"
        f"{all_entries}\n\n"
        "My weekly notes:"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=250,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

def get_daywise_partials(descs, all_days, api_key):
    """
    descs: list of dicts [{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "description": "..."}]
    all_days: list of date strings ("YYYY-MM-DD")
    Returns {date: daywise_text}
    """
    client = openai.OpenAI(api_key=api_key)
    daywise_partials = {}
    N = len(all_days)
    for i, day in enumerate(all_days):
        desc_for_day = None
        for desc in descs:
            if desc["start"] <= day <= desc["end"]:
                desc_for_day = desc["description"]
                break
        prompt = (
            f"You are writing an internship work diary for a multi-day task. "
            f"The overall task description is:\n'''{desc_for_day}'''\n"
            f"This task spans {N} days: {all_days}. "
            f"Today is day {i+1} of {N} ({day}). "
            "Write only what would logically be accomplished on this particular day, "
            "breaking down the task description into plausible progress for this day. "
            "Do NOT repeat content from other days, and do NOT include the date in your answer. "
            "Do NOT start with 'Summary for', 'On', or any date. "
            "Be brief but specific—imagine you are spreading the workload evenly or logically across the days."
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=180,
            temperature=0.2,
        )
        daywise_partials[day] = response.choices[0].message.content.strip()
    return daywise_partials

