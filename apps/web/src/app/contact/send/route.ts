import { NextResponse } from "next/server";

import { SUPPORT_EMAIL } from "@/lib/site";

/** Receives the "Talk to us" form and emails it.
 *
 *  Deliberately not under /api: next.config.ts rewrites /api/:path* to the control plane,
 *  so a route there would never run. The key lives on Vercel and never reaches the
 *  browser, and the control plane never sees any of this. Support mail is not review data
 *  and has no business crossing that boundary.
 */

const FROM = "Plug and Play Reviewer <onboarding@resend.dev>";
const RESEND_URL = "https://api.resend.com/emails";

const LIMITS = { name: 120, email: 254, message: 5000 } as const;

/** One in-memory window per instance. Not a real rate limiter across a fleet, and it does
 *  not need to be: it exists to stop a single bored visitor emptying the send quota. */
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 3;
const seen = new Map<string, number[]>();

function tooMany(key: string): boolean {
  const now = Date.now();
  const recent = (seen.get(key) ?? []).filter((at) => now - at < WINDOW_MS);
  recent.push(now);
  seen.set(key, recent);
  return recent.length > MAX_PER_WINDOW;
}

function bad(message: string, status = 400): NextResponse {
  return NextResponse.json({ ok: false, error: message }, { status });
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return bad("Send the form as JSON.");
  }

  // Honeypot. A real person never fills a field they cannot see, so a filled one is a
  // bot. Answer 200 so it learns nothing from the difference.
  if (typeof body.website === "string" && body.website.trim() !== "") {
    return NextResponse.json({ ok: true });
  }

  const name = String(body.name ?? "").trim();
  const email = String(body.email ?? "").trim();
  const message = String(body.message ?? "").trim();

  if (!name) return bad("Tell us your name so we know who we are replying to.");
  if (!email.includes("@") || email.length < 3) {
    return bad("That email address will not reach you.");
  }
  if (!message) return bad("Describe the problem and we will read it.");
  if (name.length > LIMITS.name) return bad("That name is too long.");
  if (email.length > LIMITS.email) return bad("That email address is too long.");
  if (message.length > LIMITS.message) {
    return bad(`Keep it under ${LIMITS.message} characters, or link to a gist.`);
  }

  const forwarded = request.headers.get("x-forwarded-for") ?? "unknown";
  if (tooMany(forwarded.split(",")[0].trim())) {
    return bad("That is a lot of messages at once. Try again in a minute.", 429);
  }

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    // Say so rather than pretending it sent. Someone reporting a bug deserves to know
    // their report went nowhere, and deserves an address they can use instead.
    return bad(
      `Our contact form is not configured right now. Email ${SUPPORT_EMAIL} directly and we will pick it up.`,
      503,
    );
  }

  const response = await fetch(RESEND_URL, {
    method: "POST",
    headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
    body: JSON.stringify({
      from: FROM,
      to: [SUPPORT_EMAIL],
      reply_to: email,
      subject: `Plug and Play Reviewer: ${name}`,
      text: [`From: ${name} <${email}>`, "", message].join("\n"),
    }),
  });

  if (!response.ok) {
    // Carry Resend's own reason through. It is a description of what was wrong with the
    // request ("you can only send to your own address until a domain is verified"), not a
    // secret, and without it a 502 here is unfixable from the outside.
    let reason = "";
    try {
      const detail = (await response.json()) as { message?: string };
      reason = typeof detail.message === "string" ? ` (${detail.message})` : "";
    } catch {
      reason = "";
    }
    return bad(
      `We could not send that${reason}. Email ${SUPPORT_EMAIL} directly and we will pick it up.`,
      502,
    );
  }

  return NextResponse.json({ ok: true });
}
