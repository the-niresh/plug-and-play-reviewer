import type { Metadata } from "next";

import { ContactForm } from "@/components/ContactForm";
import { SiteNav } from "@/components/SiteNav";
import { SUPPORT_EMAIL, pageTitle } from "@/lib/site";

export const metadata: Metadata = {
  title: pageTitle("Talk to Us"),
  description:
    "Report a bug in the AI PR reviewer, ask how self-hosting works, or tell us a review got it wrong. It reaches a person.",
  alternates: { canonical: "/contact" },
};

const REPO = "https://github.com/the-niresh/plug-and-play-reviewer";

const ROUTES = [
  {
    tag: "A bug, or a review that got it wrong",
    body: "Use the form. Paste the error text and say which repository it was. If the reviewer posted something wrong, a link to the pull request tells us more than any description.",
  },
  {
    tag: "Something you would rather discuss in public",
    body: "Open a GitHub issue. Other people hit the same things, and an issue is the only record they can find later.",
    href: `${REPO}/issues/new/choose`,
    label: "Open an issue",
  },
  {
    tag: "A security or data-boundary problem",
    body: "Report it privately, not in an issue, and please do not include secrets. Prompt injection and anything that could move source or a model key onto the hosted side belongs here.",
    href: `${REPO}/security/advisories/new`,
    label: "Private security report",
  },
] as const;

export default function ContactPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto w-full max-w-3xl px-6 py-14">
        <h1 className="landing-display text-3xl font-semibold tracking-tight">
          Talk to us
        </h1>
        <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
          This is a small project run by one person. There is no support queue and no bot
          on the other end. Tell us what broke and you will get a reply from someone who
          can fix it.
        </p>

        <div className="mt-10">
          <ContactForm />
        </div>

        <section className="mt-14">
          <h2 className="text-xl font-semibold tracking-tight">Where else to go</h2>
          <div className="mt-6 flex flex-col">
            {ROUTES.map((route) => (
              <div key={route.tag} className="border-t py-6">
                <p className="section-label">{route.tag}</p>
                <p className="text-muted-foreground mt-2 max-w-prose text-sm leading-relaxed">
                  {route.body}
                </p>
                {"href" in route ? (
                  <a
                    href={route.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-foreground mt-3 inline-block rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
                  >
                    {route.label}
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </section>

        <p className="text-muted-foreground mt-10 border-t pt-8 font-mono text-xs">
          Direct: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
        </p>
      </main>
    </>
  );
}
