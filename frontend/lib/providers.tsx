"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError } from "@/lib/api-client";
import { TelegramWebAppGate } from "@/components/telegram/telegram-webapp-gate";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (failureCount, error) => {
              // Don't burn retries on 4xx (bad request, not found, forbidden, etc.) — only
              // transient/server errors are worth a retry.
              if (error instanceof ApiError && error.status < 500) return false;
              return failureCount < 2;
            },
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <TelegramWebAppGate>{children}</TelegramWebAppGate>
    </QueryClientProvider>
  );
}
