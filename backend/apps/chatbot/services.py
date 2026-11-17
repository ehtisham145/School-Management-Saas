from apps.chatbot.prompts import SYSTEM_PROMPT
from apps.integrations.ai.chat_provider import send_chat_reply


def get_reply(message, history):
    trimmed_history = history[-6:]
    return send_chat_reply(message, trimmed_history, SYSTEM_PROMPT)
