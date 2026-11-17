from rest_framework import serializers


class ChatHistoryEntrySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField()


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)
    history = ChatHistoryEntrySerializer(many=True, required=False, default=list)
