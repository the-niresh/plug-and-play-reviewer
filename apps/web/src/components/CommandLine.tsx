"use client";

/** A shell command with a copy button.
 *
 *  The command people need most is a long curl that wraps in a terminal, and reading it
 *  off the screen to retype is where a character gets dropped. navigator.clipboard needs
 *  a secure context, and it can also be refused by permission policy, so the button
 *  reports a failure instead of silently pretending it copied. */

import { useCallback, useEffect, useRef, useState } from "react";

type State = "idle" | "copied" | "failed";

const LABEL: Record<State, string> = {
  idle: "Copy",
  copied: "Copied",
  failed: "Press Ctrl+C",
};

export function CommandLine({ command }: { command: string }) {
  const [state, setState] = useState<State>("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) {
        clearTimeout(timer.current);
      }
    };
  }, []);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(command);
      setState("copied");
    } catch {
      setState("failed");
    }
    if (timer.current) {
      clearTimeout(timer.current);
    }
    timer.current = setTimeout(() => setState("idle"), 2000);
  }, [command]);

  return (
    <div className="bg-muted/50 flex items-stretch gap-2 rounded-md">
      <pre className="min-w-0 flex-1 overflow-x-auto px-3 py-2.5 font-mono text-xs whitespace-pre">
        {command}
      </pre>
      <button
        type="button"
        onClick={copy}
        // The command itself is the only thing that identifies which button this is.
        aria-label={`Copy command: ${command}`}
        className="border-border/70 text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:ring-ring/50 my-1.5 mr-1.5 shrink-0 self-center rounded border px-2 py-1 font-mono text-[11px] transition-colors focus-visible:ring-[3px] focus-visible:outline-none"
      >
        {LABEL[state]}
        <span aria-live="polite" className="sr-only">
          {state === "copied" ? "Copied to clipboard" : null}
          {state === "failed" ? "Copy failed, select the text and copy it yourself" : null}
        </span>
      </button>
    </div>
  );
}
