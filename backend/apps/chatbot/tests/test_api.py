from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_chatbot_message_returns_reply(api_client):
    with patch(
        "apps.chatbot.services.send_chat_reply",
        return_value="Lesson Lab helps schools manage attendance, exams and fees.",
    ):
        response = api_client.post("/api/chatbot/message/", {"message": "What is Lesson Lab?"})

    assert response.status_code == 200
    assert "Lesson Lab" in response.data["reply"]


@pytest.mark.django_db
def test_chatbot_message_rejects_empty_message(api_client):
    response = api_client.post("/api/chatbot/message/", {"message": ""})

    assert response.status_code == 400
