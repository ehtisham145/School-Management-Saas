import { apiFetch } from "@/lib/api";
import type { ChatHistoryEntry, ChatMessageResponse } from "./schemas";

export function sendChatMessage(message: string, history: ChatHistoryEntry[]) {
  return apiFetch<ChatMessageResponse>("/chatbot/message/", {
    method: "POST",
    body: { message, history },
  });
}
