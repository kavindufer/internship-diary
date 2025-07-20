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

def get_daywise_partials(task_name, refined_text, all_days, api_key):
    """
    Given a refined task description and list of dates (strings, e.g., '2025-02-05'), 
    return a dict of {date: text} where each text is only about that day’s progress.
    """
    client = openai.OpenAI(api_key=api_key)
    daywise_partials = {}
    for i, day in enumerate(all_days):
        prompt = (
            f"This task spans {len(all_days)} days: {all_days}. "
            f"For day {i+1} ({day}), write only the specific progress and activities for that day, "
            "using the provided full description. Do not repeat prior or future days, do not duplicate content. "
            "Be concise and factual. Here's the full description:\n"
            f"{refined_text}\n\n"
            "Today's entry:"
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=200,
            temperature=0,
        )
        daywise_partials[day] = response.choices[0].message.content.strip()
    return daywise_partials
