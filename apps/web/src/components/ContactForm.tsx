"use client";

/** Talk to us. Three fields, because anything longer is a form people abandon.
 *
 *  Before this there was no way to tell us anything: the issue template existed and
 *  nothing in the product linked to it, blank issues were off, and there was no address
 *  anywhere. A bug nobody can report is a bug you never hear about. */

import { useState } from "react";

import { SUPPORT_EMAIL } from "@/lib/site";

type State =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "sent" }
  | { kind: "failed"; message: string };

export function ContactForm() {
  const [state, setState] = useState<State>({ kind: "idle" });

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setState({ kind: "sending" });

    try {
      const response = await fetch("/contact/send", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: data.get("name"),
          email: data.get("email"),
          message: data.get("message"),
          website: data.get("website"),
        }),
      });
      const payload = (await response.json()) as { ok?: boolean; error?: string };
      if (!response.ok || !payload.ok) {
        setState({
          kind: "failed",
          message: payload.error ?? "Something went wrong on our side.",
        });
        return;
      }
      form.reset();
      setState({ kind: "sent" });
    } catch {
      setState({
        kind: "failed",
        message: `We could not reach our own server. Email ${SUPPORT_EMAIL} instead.`,
      });
    }
  }

  if (state.kind === "sent") {
    return (
      <div
        role="status"
        className="border-border bg-card rounded-lg border p-6 text-sm leading-relaxed"
      >
        <p className="text-foreground font-medium">Got it, thank you.</p>
        <p className="text-muted-foreground mt-2">
          It goes to a person, not a queue. If it is urgent, {SUPPORT_EMAIL} reaches the
          same inbox.
        </p>
        <button
          type="button"
          onClick={() => setState({ kind: "idle" })}
          className="text-foreground mt-4 rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
        >
          Send another
        </button>
      </div>
    );
  }

  const sending = state.kind === "sending";

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="contact-name" className="text-sm font-medium">
          Your name
        </label>
        <input
          id="contact-name"
          name="name"
          required
          maxLength={120}
          autoComplete="name"
          className="border-border bg-background focus-visible:ring-ring/50 rounded-md border px-3 py-2 text-sm focus-visible:ring-[3px] focus-visible:outline-none"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="contact-email" className="text-sm font-medium">
          Email we can reply to
        </label>
        <input
          id="contact-email"
          name="email"
          type="email"
          required
          maxLength={254}
          autoComplete="email"
          className="border-border bg-background focus-visible:ring-ring/50 rounded-md border px-3 py-2 text-sm focus-visible:ring-[3px] focus-visible:outline-none"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="contact-message" className="text-sm font-medium">
          What happened
        </label>
        <textarea
          id="contact-message"
          name="message"
          required
          rows={6}
          maxLength={5000}
          placeholder="What you did, what you expected, what happened instead. Paste any error text."
          className="border-border bg-background focus-visible:ring-ring/50 rounded-md border px-3 py-2 text-sm leading-relaxed focus-visible:ring-[3px] focus-visible:outline-none"
        />
      </div>

      {/* Honeypot. Hidden from sight and from screen readers, and never focusable, so no
          real person can fill it in by accident. */}
      <div aria-hidden="true" className="absolute h-0 w-0 overflow-hidden">
        <label htmlFor="contact-website">Leave this empty</label>
        <input id="contact-website" name="website" tabIndex={-1} autoComplete="off" />
      </div>

      {state.kind === "failed" ? (
        <p role="alert" className="text-destructive text-sm leading-relaxed">
          {state.message}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={sending}
          className="bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-ring/50 w-fit rounded-md px-5 py-2.5 text-sm font-medium transition-colors focus-visible:ring-[3px] focus-visible:outline-none disabled:opacity-60"
        >
          {sending ? "Sending..." : "Send"}
        </button>
        <p className="text-muted-foreground text-sm">
          Or email{" "}
          <a
            href={`mailto:${SUPPORT_EMAIL}`}
            className="text-foreground rounded-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
          >
            {SUPPORT_EMAIL}
          </a>
          .
        </p>
      </div>
    </form>
  );
}
