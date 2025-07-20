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
