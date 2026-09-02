"use client";

import { useTranslations } from "next-intl";
import { Bot } from "lucide-react";

import { Card, CardDescription, CardTitle } from "@/components/ui/card";

// Phase 7 (AI Coach) hasn't been built yet — it's blocked on an OpenAI API key that hasn't been
// provided. This is an honest placeholder rather than a fake chat UI (spec.md §61: no mock data
// in production paths) so the nav link isn't a dead end.
export default function AiCoachPage() {
  const t = useTranslations("nav");

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Bot className="h-7 w-7" />
        </div>
        <CardTitle>{t("aiCoach")}</CardTitle>
        <CardDescription>
          The AI coach isn&apos;t connected yet — it needs an AI provider API key configured on the
          backend. Once that&apos;s set up, you&apos;ll be able to chat here for a personalized workout
          plan and nutrition guidance.
        </CardDescription>
      </Card>
    </div>
  );
}
