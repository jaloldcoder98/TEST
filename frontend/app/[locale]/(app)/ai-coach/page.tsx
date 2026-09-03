"use client";

/* TODO(webapp-first): TZ §16 — the spec routes this at /ai and asks for suggested questions, quick actions and
 * streamed responses (SSE). Today it is a plain buffered request/response chat.
 * Rename the route (keep a redirect from /ai-coach) and add the streaming client once the
 * backend exposes /ai/chat/stream.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Bot, Send, User as UserIcon } from "lucide-react";

import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAiChat } from "@/lib/hooks/use-ai";
import { cn } from "@/lib/utils";

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

// Real chat UI against POST /ai/chat (Phase 7). If the backend has no AI provider configured it
// returns 503 AI_NOT_CONFIGURED — shown here as an honest inline notice rather than faked replies
// (spec.md §61: no mock data in production paths), same message the Telegram bot shows.
export default function AiCoachPage() {
  const t = useTranslations("aiCoach");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [notConfigured, setNotConfigured] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const chat = useAiChat("/ai/chat");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, chat.isPending]);

  function handleReset() {
    setTurns([]);
    setConversationId(undefined);
    setNotConfigured(false);
    setErrorMessage(null);
  }

  async function handleSend() {
    const message = draft.trim();
    if (!message || chat.isPending) return;
    setErrorMessage(null);
    setTurns((prev) => [...prev, { role: "user", content: message }]);
    setDraft("");

    try {
      const response = await chat.mutateAsync({ message, conversation_id: conversationId });
      setConversationId(response.conversation_id);
      setTurns((prev) => [...prev, { role: "assistant", content: response.message }]);
    } catch (err) {
      if (err instanceof ApiError && err.code === "AI_NOT_CONFIGURED") {
        setNotConfigured(true);
        setTurns((prev) => prev.slice(0, -1));
        return;
      }
      setErrorMessage(t("errorGeneric"));
      setTurns((prev) => prev.slice(0, -1));
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        {turns.length > 0 && (
          <Button variant="secondary" size="sm" onClick={handleReset}>
            {t("newChat")}
          </Button>
        )}
      </div>

      {notConfigured ? (
        <div className="flex flex-1 items-center justify-center">
          <Card className="max-w-md text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/15 text-primary">
              <Bot className="h-7 w-7" />
            </div>
            <CardTitle>{t("notConfiguredTitle")}</CardTitle>
            <CardDescription>{t("notConfiguredBody")}</CardDescription>
          </Card>
        </div>
      ) : (
        <>
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-border bg-surface p-4">
            {turns.length === 0 && !chat.isPending && (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-muted-foreground">
                <Bot className="h-10 w-10 text-primary" />
                <p className="max-w-xs text-sm">{t("subtitle")}</p>
              </div>
            )}
            {turns.map((turn, i) => (
              <div key={i} className={cn("flex gap-3", turn.role === "user" && "flex-row-reverse")}>
                <div
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                    turn.role === "user" ? "bg-surface-2 text-foreground" : "bg-primary/15 text-primary"
                  )}
                >
                  {turn.role === "user" ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div
                  className={cn(
                    "max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm",
                    turn.role === "user" ? "bg-primary text-primary-foreground" : "bg-surface-2 text-foreground"
                  )}
                >
                  {turn.content}
                </div>
              </div>
            ))}
            {chat.isPending && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="flex items-center gap-2 rounded-2xl bg-surface-2 px-4 py-2.5 text-sm text-muted-foreground">
                  <Spinner className="h-4 w-4" />
                  {t("thinking")}
                </div>
              </div>
            )}
          </div>

          {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              void handleSend();
            }}
            className="flex items-end gap-2"
          >
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              placeholder={t("placeholder")}
              rows={1}
              className="flex-1 resize-none rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-primary"
            />
            <Button type="submit" disabled={!draft.trim() || chat.isPending}>
              <Send className="h-4 w-4" />
              {t("send")}
            </Button>
          </form>
        </>
      )}
    </div>
  );
}
