import Link from "next/link";
import { Dumbbell } from "lucide-react";

export function AuthShell({
  title,
  subtitle,
  locale,
  children,
}: {
  title: string;
  subtitle: string;
  locale: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-12">
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[-10rem] h-[30rem] w-[30rem] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]"
      />
      <div className="relative z-10 w-full max-w-md">
        <Link
          href={`/${locale}`}
          className="mb-8 flex items-center justify-center gap-2 text-lg font-bold tracking-tight"
        >
          <Dumbbell className="h-6 w-6 text-primary" />
          GYM<span className="text-primary">AI</span>
        </Link>
        <div className="rounded-2xl border border-border bg-surface p-8">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}
