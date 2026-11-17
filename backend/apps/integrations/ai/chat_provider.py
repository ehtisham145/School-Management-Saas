from django.conf import settings
from openai import OpenAI

_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def send_chat_reply(message, history, system_prompt):
    messages = [{"role": "system", "content": system_prompt}]
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": message})

    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300,
    )
    return response.choices[0].message.content
