from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.chatbot.api.serializers import ChatMessageSerializer
from apps.chatbot.services import get_reply


class ChatbotMessageView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chatbot"

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reply = get_reply(
            serializer.validated_data["message"],
            serializer.validated_data["history"],
        )
        return Response({"reply": reply})
