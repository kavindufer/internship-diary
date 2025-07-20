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
