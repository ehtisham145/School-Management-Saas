from django.urls import path

from apps.chatbot.api.views import ChatbotMessageView

urlpatterns = [
    path("message/", ChatbotMessageView.as_view(), name="chatbot-message"),
]
