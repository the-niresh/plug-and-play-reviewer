import type { Metadata } from "next";
import Link from "next/link";

import { SiteNav } from "@/components/SiteNav";
import { PRODUCT_NAME, pageTitle, siteHost } from "@/lib/site";

export const metadata: Metadata = {
  title: pageTitle("Privacy"),
  description:
    "What the hosted control plane stores, what never leaves your runner, and the schema check that enforces the line.",
};

/** Mirrors docs/DATA_BOUNDARIES.md, which is generated from
 *  control_plane/boundary.py:ALLOWLIST. If that allowlist changes, this page is stale.
 *  Do not describe a boundary here that the schema check does not actually enforce. */
const HOSTED = [
  "Your GitHub account login, and the ids of repositories you connected.",
  "Job state for each review: which pull request, which commit, and whether it succeeded.",
  "Lifecycle events, flattened to identifiers, enum values, and token and cost totals. A database constraint rejects nested objects, so a findings list or a diff cannot be written here.",
  "Finding title, rationale, category and file path, so the dashboard can show you a review.",
  "The public text of replies people write on our review comments, used to build improvement candidates a human then reviews.",
  "Hashes: runner credentials, pairing codes, OAuth state, and notification webhook URLs. The originals are never stored.",
] as const;

const NEVER_HOSTED = [
  "Your source code.",
  "Your diffs.",
  "Your model provider API key.",
  "Retrieval chunks, evidence, and sandbox logs.",
  "Embeddings.",
] as const;

const LOCAL = [
  "Your source and diffs, fetched with a short-lived GitHub installation token.",
  "Your model provider API key, in your operating system keychain, or a local file when no keychain exists.",
  "The local review cache and retrieval index.",
] as const;

export default function PrivacyPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto w-full max-w-3xl px-6 py-14">
        <h1 className="landing-display text-3xl font-semibold tracking-tight">
          Privacy
        </h1>
        <p className="text-muted-foreground mt-3 leading-relaxed">
          {PRODUCT_NAME} is two programs. A hosted control plane at {siteHost()} takes
          GitHub events and stores job metadata. A runner on your own machine reads the
          code and calls your model. This page says exactly what each one holds.
        </p>

        <section className="mt-12 border-t pt-8">
          <p className="section-label">
            Enforcement
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            This is a schema rule, not a promise
          </h2>
          <p className="text-muted-foreground mt-3 leading-relaxed">
            Every column on every hosted table is either a scalar type that cannot hold
            free text, or a column allowlisted one by one with a written reason. A check
            named <code className="font-mono text-xs">assert_no_private_columns</code>{" "}
            reads the live schema and fails if anything else appears. It runs in CI. If
            someone adds a hosted column that could carry source, a diff, or a key, the
            build breaks before it ships.
          </p>
        </section>

        <section className="mt-8 border-t pt-8">
          <p className="section-label">
            Hosted
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            What the hosted control plane stores
          </h2>
          <ul className="text-muted-foreground mt-4 space-y-2 text-sm leading-relaxed">
            {HOSTED.map((item) => (
              <li key={item} className="border-border border-l-2 pl-4">
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-8 border-t pt-8">
          <p className="section-label">
            Never hosted
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            What never reaches our servers
          </h2>
          <ul className="text-muted-foreground mt-4 space-y-2 text-sm leading-relaxed">
            {NEVER_HOSTED.map((item) => (
              <li key={item} className="border-border border-l-2 pl-4">
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-8 border-t pt-8">
          <p className="section-label">
            Local
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            What stays on your runner
          </h2>
          <ul className="text-muted-foreground mt-4 space-y-2 text-sm leading-relaxed">
            {LOCAL.map((item) => (
              <li key={item} className="border-border border-l-2 pl-4">
                {item}
              </li>
            ))}
          </ul>
          <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
            Your runner sends your diff to whichever model provider you configured. That
            provider&rsquo;s own terms apply to that call. We are not in the middle of it
            and we never see your key.
          </p>
        </section>

        <section className="mt-8 border-t pt-8">
          <p className="section-label">
            Cookies
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            One necessary cookie, and analytics only if you agree
          </h2>
          <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
            We set one cookie,{" "}
            <code className="font-mono text-xs">gh_live_sign_in</code>, which keeps you
            signed in. It is strictly necessary. Without it the site cannot tell that it
            is you, so there is nothing to consent to.
          </p>
          <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
            Anonymous page-view analytics are separate and off until you accept them.
            Declining prevents the script from loading at all, rather than loading it and
            hiding the notice. Your answer is stored in your own browser. Clear your site
            data to be asked again.
          </p>
        </section>

        <section className="mt-8 border-t pt-8">
          <p className="section-label">
            Your data
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            Removing it
          </h2>
          <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
            Uninstall the GitHub App to stop all new events. To have stored job metadata
            and finding text deleted, open an issue or use the contact route in{" "}
            <Link
              href="https://github.com/the-niresh/plug-and-play-reviewer/blob/main/SECURITY.md"
              className="text-foreground rounded-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
            >
              SECURITY.md
            </Link>
            . Anything on your own runner is already yours to delete:{" "}
            <code className="font-mono text-xs">reviewer uninstall</code> removes it.
          </p>
        </section>

        <p className="text-muted-foreground mt-12 border-t pt-8 font-mono text-xs">
          This project is open source. If this page and the code disagree, the code is
          the truth and the page is a bug. Please report it.
        </p>
      </main>
    </>
  );
}
