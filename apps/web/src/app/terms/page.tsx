import type { Metadata } from "next";
import Link from "next/link";

import { SiteNav } from "@/components/SiteNav";
import { PRODUCT_NAME, pageTitle } from "@/lib/site";

export const metadata: Metadata = {
  title: pageTitle("Terms"),
  description:
    "Terms of use: what the reviewer is, what it is not, who pays the model bill, and the absence of any warranty.",
};

const TERMS = [
  {
    tag: "What this is",
    title: "A review assistant, not an approver",
    body: [
      `${PRODUCT_NAME} reads a pull request and suggests findings. A human decides what gets posted. No finding reaches your repository until a person approves it.`,
      "It is not a security audit, a compliance control, or a substitute for review by someone who knows the code. Do not treat a clean run as proof that a change is safe.",
      "It misses real bugs and it raises findings that are wrong. The scorecard shows the measured rate on the sample we ran.",
    ],
  },
  {
    tag: "Your model bill",
    title: "You bring the key, you pay the provider",
    body: [
      "The runner calls whichever model provider you configured, using your own API key or provider plan. That bill is between you and them.",
      "We do not resell model access, mark it up, or hold your key. We cannot refund a provider charge and we cannot cap your spend on their side.",
      "Set your own spend limits with your provider before you point this at a busy repository.",
    ],
  },
  {
    tag: "The free tier",
    title: "One GitHub user, one repository",
    body: [
      "The hosted control plane allows one GitHub user and one repository per installation on the free tier.",
      "Self-hosting is not limited by that. The code is MIT and you can run the whole thing yourself.",
    ],
  },
  {
    tag: "Acceptable use",
    title: "Repositories you are allowed to review",
    body: [
      "Only connect repositories you own or have permission to review. You are responsible for having that permission.",
      "Do not use this to process code you were not given access to.",
    ],
  },
  {
    tag: "Availability",
    title: "No uptime promise",
    body: [
      "The hosted control plane is a free service run by one person. It may be slow, down, or discontinued.",
      "Your runner and your data are local, so you keep working when the hosted side does not. That is the point of the split.",
    ],
  },
  {
    tag: "Warranty",
    title: "None, as the licence says",
    body: [
      "The software is provided as is, without warranty of any kind, express or implied. The MIT licence in the repository governs the code and its wording controls.",
      "To the extent the law allows, we are not liable for any damage arising from use of the software or the hosted service, including a bug it failed to catch.",
    ],
  },
] as const;

export default function TermsPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto w-full max-w-3xl px-6 py-14">
        <h1 className="landing-display text-3xl font-semibold tracking-tight">Terms</h1>
        <p className="text-muted-foreground mt-3 leading-relaxed">
          Plain terms for a free, open source tool. If any of this conflicts with the{" "}
          <Link
            href="https://github.com/the-niresh/plug-and-play-reviewer/blob/main/LICENSE"
            className="text-foreground rounded-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
          >
            MIT licence
          </Link>
          , the licence wins.
        </p>

        <div className="mt-12 flex flex-col">
          {TERMS.map((section) => (
            <section key={section.tag} className="border-t py-8">
              <p className="section-label">{section.tag}</p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight">
                {section.title}
              </h2>
              <div className="text-muted-foreground mt-3 space-y-2 text-sm leading-relaxed">
                {section.body.map((sentence) => (
                  <p key={sentence}>{sentence}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <p className="text-muted-foreground border-t pt-8 font-mono text-xs">
          See also the{" "}
          <Link
            href="/privacy"
            className="text-foreground rounded-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
          >
            privacy policy
          </Link>
          .
        </p>
      </main>
    </>
  );
}
