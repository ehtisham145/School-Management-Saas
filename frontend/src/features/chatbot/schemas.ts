export type ChatRole = "user" | "assistant";

export type ChatHistoryEntry = {
  role: ChatRole;
  content: string;
};

export type ChatMessageResponse = {
  reply: string;
};
