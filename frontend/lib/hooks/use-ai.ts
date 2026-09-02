"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { ChatResponse } from "@/lib/types";

interface AiChatInput {
  message: string;
  conversation_id?: string;
}

// One hook backs both the AI Coach page (fitness Q&A) and, if reused later, a nutrition-focused
// chat — both routes return the same ChatResponse shape (app/schemas/ai.py: ChatResponse).
export function useAiChat(endpoint: "/ai/chat" | "/ai/nutrition" = "/ai/chat") {
  return useMutation({
    mutationFn: (input: AiChatInput) => api.post<ChatResponse>(endpoint, input),
  });
}
