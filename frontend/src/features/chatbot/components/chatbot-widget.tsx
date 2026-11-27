"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  Bot,
  MessageCircle,
  RotateCcw,
  Send,
  ThumbsDown,
  ThumbsUp,
  UserRound,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { ApiError } from "@/lib/api";
import { sendChatMessage } from "../api";
import type { ChatHistoryEntry } from "../schemas";

type Feedback = "up" | "down";

const QUICK_REPLY_KEYS = ["pricing", "features", "demo"] as const;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .map((part, index) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={`${keyPrefix}-${index}`}>{part.slice(2, -2)}</strong>
      ) : (
        <span key={`${keyPrefix}-${index}`}>{part}</span>
      ),
    );
}

/** Minimal formatting for bot replies: **bold**, "- " bullet lists, blank-line paragraphs. */
function renderFormatted(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  function flushList(key: string) {
    if (listItems.length === 0) return;
    nodes.push(
      <ul key={key} className="list-disc ps-5">
        {listItems.map((item, index) => (
          <li key={index}>{renderInline(item, `${key}-${index}`)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  }

  text.split("\n").forEach((line, index) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      listItems.push(trimmed.slice(2));
      return;
    }
    flushList(`list-${index}`);
    if (trimmed.length > 0) {
      nodes.push(<p key={index}>{renderInline(trimmed, `p-${index}`)}</p>);
    }
  });
  flushList("list-end");

  return nodes;
}

export function ChatbotWidget() {
  const t = useTranslations("Chatbot");
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatHistoryEntry[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({});

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  function handleFeedback(index: number, value: Feedback) {
    setFeedback((prev) => {
      const next = { ...prev };
      if (next[index] === value) {
        delete next[index];
      } else {
        next[index] = value;
      }
      return next;
    });
  }

  function handleNewConversation() {
    setMessages([]);
    setFeedback({});
    setError(null);
  }

  async function sendMessage(text: string) {
    if (!text || isSending) return;
    const history = messages;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setError(null);
    setIsSending(true);

    try {
      const { reply } = await sendChatMessage(text, history);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      if (err instanceof ApiError && err.retryAfter) {
        setError(t("rateLimited", { seconds: err.retryAfter }));
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t("error"));
      }
    } finally {
      setIsSending(false);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    await sendMessage(text);
  }

  return (
    <>
      <button
        type="button"
        aria-label={open ? t("close") : t("open")}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="fixed end-4 bottom-[76px] z-40 grid size-12 place-items-center rounded-full bg-orange text-on-orange shadow-whatsapp transition-transform hover:scale-[1.07] sm:end-[22px] sm:bottom-[94px] sm:size-[58px]"
      >
        <MessageCircle aria-hidden="true" className="size-7" />
      </button>

      {open && (
        <div className="fixed end-4 bottom-[136px] z-40 flex h-[min(560px,70dvh)] w-[min(380px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-line bg-bg shadow-soft sm:end-[22px] sm:bottom-[166px]">
          <div className="flex items-center justify-between gap-2 border-b border-line bg-navy px-4 py-3 text-on-dark">
            <div className="flex items-center gap-2.5">
              <span className="grid size-9 shrink-0 place-items-center rounded-full bg-orange text-on-orange">
                <Bot aria-hidden="true" className="size-5" />
              </span>
              <div>
                <p className="text-sm leading-tight font-bold">{t("title")}</p>
                <p className="flex items-center gap-1.5 text-xs text-on-dark-soft">
                  <span aria-hidden="true" className="size-1.5 rounded-full bg-whatsapp" />
                  {t("online")}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  type="button"
                  aria-label={t("newConversation")}
                  onClick={handleNewConversation}
                  className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-control text-on-dark-soft hover:bg-on-dark-line hover:text-on-dark"
                >
                  <RotateCcw aria-hidden="true" className="size-4" />
                </button>
              )}
              <button
                type="button"
                aria-label={t("close")}
                onClick={() => setOpen(false)}
                className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-control text-on-dark-soft hover:bg-on-dark-line hover:text-on-dark"
              >
                <X aria-hidden="true" className="size-4" />
              </button>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="flex flex-col gap-3">
                <div className="flex items-end gap-2">
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-orange text-on-orange">
                    <Bot aria-hidden="true" className="size-4" />
                  </span>
                  <div className="max-w-[78%] rounded-2xl rounded-es-sm bg-bg-tint px-3.5 py-2.5 text-sm text-ink shadow-sm">
                    {t("greeting")}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 ps-9">
                  {QUICK_REPLY_KEYS.map((key) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => sendMessage(t(`quickReplies.${key}`))}
                      className="cursor-pointer rounded-full border border-line bg-bg px-3 py-1.5 text-xs font-medium text-navy hover:bg-navy-soft"
                    >
                      {t(`quickReplies.${key}`)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((entry, index) => (
              <div
                key={index}
                className={cn("flex items-end gap-2", entry.role === "user" && "flex-row-reverse")}
              >
                <span
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-full",
                    entry.role === "user" ? "bg-navy text-on-dark" : "bg-orange text-on-orange",
                  )}
                >
                  {entry.role === "user" ? (
                    <UserRound aria-hidden="true" className="size-4" />
                  ) : (
                    <Bot aria-hidden="true" className="size-4" />
                  )}
                </span>

                <div
                  className={cn(
                    "flex max-w-[78%] flex-col gap-1",
                    entry.role === "user" && "items-end",
                  )}
                >
                  <div
                    className={cn(
                      "space-y-1 rounded-2xl px-3.5 py-2.5 text-sm shadow-sm",
                      entry.role === "user"
                        ? "rounded-ee-sm bg-navy text-on-dark"
                        : "rounded-es-sm bg-bg-tint text-ink",
                    )}
                  >
                    {entry.role === "assistant" ? renderFormatted(entry.content) : entry.content}
                  </div>

                  {entry.role === "assistant" && (
                    <div className="flex items-center gap-1 ps-1">
                      <button
                        type="button"
                        aria-label={t("helpful")}
                        aria-pressed={feedback[index] === "up"}
                        onClick={() => handleFeedback(index, "up")}
                        className={cn(
                          "flex size-6 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-bg-tint hover:text-navy",
                          feedback[index] === "up" && "text-whatsapp",
                        )}
                      >
                        <ThumbsUp aria-hidden="true" className="size-3.5" />
                      </button>
                      <button
                        type="button"
                        aria-label={t("notHelpful")}
                        aria-pressed={feedback[index] === "down"}
                        onClick={() => handleFeedback(index, "down")}
                        className={cn(
                          "flex size-6 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-bg-tint hover:text-navy",
                          feedback[index] === "down" && "text-destructive",
                        )}
                      >
                        <ThumbsDown aria-hidden="true" className="size-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isSending && (
              <div className="flex items-end gap-2">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-orange text-on-orange">
                  <Bot aria-hidden="true" className="size-4" />
                </span>
                <div className="flex items-center gap-1 rounded-2xl rounded-es-sm bg-bg-tint px-3.5 py-3.5">
                  <span className="size-1.5 animate-bounce rounded-full bg-ink-soft [animation-delay:-0.3s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-ink-soft [animation-delay:-0.15s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-ink-soft" />
                </div>
              </div>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-line p-3"
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={t("placeholder")}
              disabled={isSending}
              className="min-w-0 flex-1 rounded-control border border-line bg-bg px-3 py-2 text-sm text-ink placeholder:text-ink-soft focus:ring-2 focus:ring-orange focus:outline-none"
            />
            <button
              type="submit"
              disabled={isSending || !input.trim()}
              aria-label={t("send")}
              className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-control bg-orange text-on-orange disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send aria-hidden="true" className="size-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
