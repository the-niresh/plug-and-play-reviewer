import type { Metadata } from "next";
import Link from "next/link";

import { GithubMark } from "@/components/github-mark";
import { ProductStage } from "@/components/landing/ProductStage";
import { SiteNav } from "@/components/SiteNav";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PRODUCT_NAME, pageTitle, siteHost } from "@/lib/site";
import type { ReviewFinding } from "@/lib/reviews";

export const metadata: Metadata = {
  title: pageTitle(),
  description:
    "Private AI code review. Hosted jobs, a local runner, and your own LLM provider API key.",
};

const SIGN_IN_URL = "/api/auth/github/sign-in?return_to=/dashboard";

const RENDER_DEPLOY_URL =
  process.env.NEXT_PUBLIC_RENDER_DEPLOY_URL ??
  "https://render.com/deploy?repo=https://github.com/the-niresh/plug-and-play-reviewer";

const RAILWAY_DEPLOY_URL =
  process.env.NEXT_PUBLIC_RAILWAY_DEPLOY_URL ??
  // Railway's repo-deploy form. Verified 2026-09-11: the /new/github.com/<owner>/<repo>
  // shape 404s, this one resolves.
  "https://railway.com/new/template?template=https://github.com/the-niresh/plug-and-play-reviewer";

const SELF_HOST_DOC_URL =
  "https://github.com/the-niresh/plug-and-play-reviewer/blob/main/docs/SELF_HOST_CONTROL_PLANE.md";

const EXAMPLE_FINDING: ReviewFinding = {
  id: "example-finding",
  concern: "security",
  severity: "high",
  category: "auth",
  file_path: "src/auth/session.py",
  line_start: 88,
  line_end: 94,
  title: "Session cookie set without the Secure flag",
  rationale:
    "The new handler writes the session cookie on HTTP. A network observer can steal it.",
  verified: false,
  status: "pending",
  receipt: {
    provider: "openai",
    model: "gpt-4o-mini",
    input_tokens: null,
    output_tokens: null,
    cost_usd: null,
    verification_status: "asserted",
    verification_reason: "No sandbox run. A human still has to approve posting.",
    sandbox_run_id: null,
    command_id: null,
    verification_detail: null,
    context_sources: [],
  },
};

const FLOW_STEPS = [
  {
    title: "GitHub PR",
    body: "The GitHub App receives the pull request event and the head SHA.",
  },
  {
    title: "hosted job",
    body: "The control plane stores job metadata only. It does not receive the diff.",
  },
  {
    title: "local runner",
    body: "Your runner claims the job, fetches the patch, and keeps the source local.",
  },
  {
    title: "retrieval",
    body: "Repo chunks join the packed diff before the model call.",
  },
  {
    title: "review comment",
    body: "A comment does not post until a human approves it.",
  },
] as const;

const PRIDE = [
  {
    title: "Local runner",
    body:
      "The model call happens on your laptop or server. Source never goes to the hosted site. The hosted plane only ever learns that a job ran, which repository it was for, and what it cost.",
  },
  {
    title: "Retrieval",
    body: "The reviewer gets repo chunks with the packed diff. It is not a diff-only guess.",
  },
  {
    title: "Grounding",
    body: "A finding that cannot point at the packed hunk is dropped before anyone sees it.",
  },
  {
    title: "Suggested fixes",
    body: "An optional suggested_fix can post as a GitHub suggestion when the replacement applies.",
  },
  {
    title: "Opt-in specialists",
    body: "Extra reviewers run only when a repo turns them on. They are off by default.",
  },
  {
    title: "Human gate",
    body: "The model cannot mark a finding public. Posting stays a human action.",
  },
] as const;

const PRIVACY_ROWS = [
  { item: "Source code", hosted: "Never", local: "Yes, on the runner" },
  { item: "Diffs", hosted: "Never", local: "Yes, packed for the model" },
  {
    item: "Your LLM provider API key",
    hosted: "Never",
    local: "Yes, in the local key store",
  },
  { item: "GitHub event metadata", hosted: "Yes", local: "Yes, to claim the job" },
  {
    item: "Finding title and rationale",
    hosted: "Yes, so the dashboard can show it",
    local: "Produced here",
  },
] as const;

const SETUP_STEPS = [
  {
    title: "GitHub App",
    body: "Install the GitHub App and pick the repositories it may read.",
  },
  {
    title: "Hosted URL",
    body: `Point the runner at the hosted URL. ${siteHost()} is the live control plane.`,
  },
  {
    title: "Local runner",
    body: "Install the runner on the machine that may see your source.",
  },
  {
    title: "Your LLM provider API key",
    body:
      "The key from OpenAI, Anthropic, Groq or whoever you use. It stays on the runner and never reaches the hosted database.",
  },
] as const;

const SECTIONS = [
  { id: "how-a-review-moves", title: "How a review moves" },
  { id: "hosted-vs-local", title: "Hosted vs local" },
  { id: "what-already-works", title: "What already works" },
  { id: "what-teams-can-change", title: "What teams can change" },
  { id: "what-the-evals-show", title: "What the evals show" },
  { id: "how-to-set-it-up", title: "How to set it up" },
] as const;

export default function HomePage() {
  return (
    <div className="landing-root">
      <a
        href="#how-a-review-moves"
        className="bg-foreground text-background focus:ring-ring absolute left-4 z-50 -translate-y-[120%] px-3 py-2 text-sm focus:translate-y-4 focus:ring-2 focus:outline-none"
      >
        Skip to how a review moves
      </a>
      <SiteNav />
      <main className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <section className="border-border grid gap-10 border-b py-14 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:items-end lg:gap-14 lg:py-20">
          <div className="min-w-0">
            <p className="section-label">{PRODUCT_NAME}</p>
            <p className="text-muted-foreground mt-4 text-sm">
              Built for solo devs shipping 2 to 3 pull requests a day
            </p>
            <h1 className="landing-display landing-hero-title mt-6 max-w-[14ch] font-semibold text-balance">
              Private AI code review that stays on your machine
            </h1>
            <p className="text-muted-foreground mt-6 max-w-prose text-lg leading-relaxed">
              A hosted control plane takes GitHub events. Your local runner reads the diff
              and calls your model. The patch never leaves the machine you trust.
            </p>
            <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
              That boundary is not a promise on a slide. CI runs a schema check that fails
              if source, diffs, or provider keys could land on the hosted plane. See what we
              store in{" "}
              <Link
                href="/privacy"
              className="landing-link"
            >
              Privacy
            </Link>
              .
            </p>
            <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
              An open source PR reviewer built for private AI code review.
              It is AI code review self hosted on a laptop or a server you run.
            </p>
            <p className="text-muted-foreground mt-8 max-w-prose text-sm leading-relaxed">
              Self-hosting the control plane needs a GitHub App before you click either
              button below. Read{" "}
              <a
                href={SELF_HOST_DOC_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="landing-link"
              >
                Self-host the control plane
              </a>{" "}
              first.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:flex sm:flex-wrap sm:items-center">
              <a
                href={SIGN_IN_URL}
                className={cn(buttonVariants({ size: "lg" }), "w-fit gap-2")}
              >
                <GithubMark className="size-4" />
                Sign in with GitHub
              </a>
              <a
                href={RENDER_DEPLOY_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center focus-visible:ring-ring/50 rounded-md focus-visible:ring-[3px] focus-visible:outline-none"
              >
                {/* Official button, served from /public, not hot-linked.
                    Fetching it from render.com would report every visitor to them.
                    This page claims nothing leaks, so nothing may leak. */}
                <img
                  src="/deploy-to-render.svg"
                  alt="Deploy API on Render"
                  width={153}
                  height={40}
                />
              </a>
              <a
                href={RAILWAY_DEPLOY_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center focus-visible:ring-ring/50 rounded-md focus-visible:ring-[3px] focus-visible:outline-none"
              >
                <img
                  src="/deploy-on-railway.svg"
                  alt="Deploy API on Railway"
                  width={183}
                  height={40}
                />
              </a>
            </div>
            <a href="#how-a-review-moves" className="landing-link mt-6 inline-block text-sm">
              See how a review moves
            </a>
          </div>
          <div className="landing-rule min-w-0 lg:translate-y-3">
            <ProductStage finding={EXAMPLE_FINDING} />
          </div>
        </section>

        <section
          id="how-a-review-moves"
          className="border-border scroll-mt-20 border-b py-14 lg:py-[var(--space-section)]"
        >
          <h2 className="landing-display landing-section-title font-semibold">
            {SECTIONS[0].title}
          </h2>
          <p className="text-muted-foreground mt-4 max-w-prose text-base leading-relaxed">
            GitHub PR to hosted job to local runner to retrieval to review comment. The
            hosted box never holds the patch.
          </p>
          <ol className="mt-10 grid gap-0 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1.2fr]">
            {FLOW_STEPS.map((step, index) => (
              <li
                key={step.title}
                className={cn(
                  "border-border min-w-0 border-t px-0 py-5",
                  "lg:border-t-0 lg:border-l lg:px-4 lg:first:border-l-0 lg:first:pl-0",
                  index > 0 && "lg:pt-0",
                )}
              >
                <h3 className="font-mono text-sm font-semibold">{step.title}</h3>
                <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section
          id="hosted-vs-local"
          className="border-border scroll-mt-20 border-b py-12 lg:py-20"
        >
          <h2 className="landing-display landing-section-title font-semibold">
            {SECTIONS[1].title}
          </h2>
          <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
            Source, diffs, and your provider API key stay on the runner. Finding text may sit on
            the dashboard so you can read it before you approve a post.
          </p>
          <div className="mt-8 grid gap-0 sm:grid-cols-2 lg:hidden">
            {PRIVACY_ROWS.map((row, index) => (
              <article
                key={row.item}
                className={cn(
                  "border-border border-t px-0 py-4",
                  index % 2 === 1 && "sm:border-l sm:pl-4",
                )}
              >
                <h3 className="font-mono text-sm font-semibold">{row.item}</h3>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <dt className="text-foreground text-[11px] font-semibold">
                      Hosted
                    </dt>
                    <dd className="text-muted-foreground mt-1">{row.hosted}</dd>
                  </div>
                  <div>
                    <dt className="text-foreground text-[11px] font-semibold">
                      Local
                    </dt>
                    <dd className="text-muted-foreground mt-1">{row.local}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
          <div className="landing-rule mt-8 hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[36rem] border-collapse text-sm">
              <caption className="sr-only">
                What the hosted control plane sees versus what stays on the local runner
              </caption>
              <thead>
                <tr className="bg-muted/40 text-muted-foreground text-left">
                  <th scope="col" className="px-4 py-3 font-medium">
                    Data
                  </th>
                  <th scope="col" className="text-foreground px-4 py-3 font-semibold">
                    Hosted
                  </th>
                  <th scope="col" className="text-foreground px-4 py-3 font-semibold">
                    Local
                  </th>
                </tr>
              </thead>
              <tbody>
                {PRIVACY_ROWS.map((row) => (
                  <tr key={row.item} className="border-border border-t">
                    <th scope="row" className="px-4 py-3 text-left font-medium">
                      {row.item}
                    </th>
                    <td className="text-muted-foreground px-4 py-3">{row.hosted}</td>
                    <td className="text-muted-foreground px-4 py-3">{row.local}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section
          id="what-already-works"
          className="border-border scroll-mt-20 border-b py-[var(--space-section)]"
        >
          <h2 className="landing-display landing-section-title font-semibold">
            {SECTIONS[2].title}
          </h2>
          <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
            Grounded findings, suggestion blocks, and the human gate are product rules, not
            slogans.
          </p>
          <div className="mt-10 grid gap-0 lg:grid-cols-12">
            {PRIDE.map((item, index) => (
              <article
                key={item.title}
                className={cn(
                  "border-border border-t px-0 py-5",
                  "lg:border-t-0 lg:border-l lg:px-5 lg:py-6",
                  "lg:first:border-l-0 lg:first:pl-0",
                  index === 0 ? "lg:col-span-7" : "lg:col-span-5",
                  index > 0 && index % 2 === 1 && "lg:col-start-8",
                )}
              >
                <h3 className="font-mono text-sm font-semibold">{item.title}</h3>
                <p
                  className={cn(
                    "text-muted-foreground mt-2 leading-relaxed",
                    index === 0 ? "max-w-prose text-base" : "text-sm",
                  )}
                >
                  {item.body}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section
          id="what-teams-can-change"
          className="border-border scroll-mt-20 grid gap-10 border-b py-12 lg:grid-cols-2 lg:gap-16 lg:py-20"
        >
          <article>
            <h2 className="landing-display landing-section-title font-semibold">
              {SECTIONS[3].title}
            </h2>
            <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
              You can add agents and edit prompts per repository. Those settings stay
              private to that repo.
            </p>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              Repo A never receives Repo B prompts. This is permissioned team power, not a
              public dump.
            </p>
          </article>
          <article className="border-border border-t pt-6 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8">
            <p className="section-label">Access shape</p>
            <h2 className="landing-display landing-section-title mt-2 font-semibold">
              What stays free and what is for teams
            </h2>
            <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
              A single person running a local reviewer can stay on a simple path.
              The free tier allows one GitHub user and one repository per installation.
            </p>
            <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
              Team controls, shared prompts, and extra repositories are the paid path. There
              are no prices on this page.
            </p>
          </article>
        </section>

        <section
          id="what-the-evals-show"
          className="border-border scroll-mt-20 border-b py-14 lg:py-[var(--space-section)]"
        >
          <h2 className="landing-display landing-section-title font-semibold">
            {SECTIONS[4].title}
          </h2>
          <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
            Every finding is scored by a second model call and anything ungrounded is
            dropped before you see it. The scorecard shows the measured result on a
            human-judged holdout, with the model and the sample it was run on.
            That holdout is seven human-judged cases from the Zod repository, so it is
            evidence, not a published baseline.
          </p>
          <Link href="/scorecard" className="landing-link mt-8 inline-block text-sm font-medium">
            Open the scorecard
          </Link>
        </section>

        <section
          id="how-to-set-it-up"
          className="border-border scroll-mt-20 grid gap-12 border-b py-12 lg:grid-cols-[1.1fr_0.9fr] lg:py-20"
        >
          <div>
            <h2 className="landing-display landing-section-title font-semibold">
              {SECTIONS[5].title}
            </h2>
            <ol className="mt-8 flex flex-col gap-3">
              {SETUP_STEPS.map((step) => (
                <li
                  key={step.title}
                  className="border-border border-t px-0 py-4 first:border-t-0 first:pt-0"
                >
                  <p className="font-mono text-sm font-semibold">{step.title}</p>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                    {step.body}
                  </p>
                </li>
              ))}
            </ol>
            <p className="text-muted-foreground mt-5 max-w-prose text-sm leading-relaxed">
              Step 02 is the only part you can hand to a host. These deploy the control
              plane, not the runner: the runner must stay on a machine you trust, which is
              the whole point.
            </p>
            <p className="text-muted-foreground mt-4 max-w-prose text-sm leading-relaxed">
              Self-hosting the control plane still needs your own secrets and database.
              Railway starts from a repo import until a public template id exists.
            </p>
            <Link
              href="/docs"
              className="landing-link mt-4 inline-block text-sm"
            >
              Read the install docs
            </Link>
          </div>
          <aside className="border-border border-t pt-6 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8">
            <p className="section-label">Not automatic yet</p>
            <h2 className="landing-display landing-section-title mt-2 font-semibold">
              What is not automatic yet
            </h2>
            <ul className="text-muted-foreground mt-4 space-y-3 text-sm leading-relaxed">
              <li>The reviewer does not learn from human replies yet.</li>
              <li>
                The published scorecard is a narrow holdout sample, not a guarantee on your
                repository.
              </li>
              <li>
                An empty-generate retry exists but stays off. It raised false findings when
                we tried it.
              </li>
            </ul>
          </aside>
        </section>

        <footer className="text-muted-foreground border-border border-t py-10 font-mono text-xs">
          <p>
            {PRODUCT_NAME} · {siteHost()}
          </p>
          <p className="mt-2">Built for fast shipping solo founders.</p>
          <nav aria-label="Legal" className="mt-4 flex flex-wrap gap-4">
            <Link
              href="/privacy"
              className="landing-link"
            >
              Privacy
            </Link>
            <Link href="/terms" className="landing-link">
              Terms
            </Link>
          </nav>
        </footer>
      </main>
    </div>
  );
}
