import Link from "next/link";

import { RailwayMark, RenderMark, VercelMark } from "@/components/deploy-marks";
import { GithubMark } from "@/components/github-mark";
import { ProductStage } from "@/components/landing/ProductStage";
import { SiteNav } from "@/components/SiteNav";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PRODUCT_NAME, pageTitle, siteHost } from "@/lib/site";
import type { ReviewFinding } from "@/lib/reviews";

export const metadata = {
  title: pageTitle(),
  description:
    "Private AI code review. Hosted jobs, a local runner, and your own LLM provider API key.",
};

const SIGN_IN_URL = "/api/auth/github/sign-in?return_to=/dashboard";

const VERCEL_DEPLOY_URL =
  process.env.NEXT_PUBLIC_VERCEL_DEPLOY_URL ??
  "https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fthe-niresh%2Fplug-and-play-reviewer&project-name=pr-reviewer-web&repository-name=plug-and-play-reviewer&env=NEXT_PUBLIC_SITE_ORIGIN,NEXT_PUBLIC_CONTROL_PLANE_ORIGIN,NEXT_PUBLIC_GITHUB_APP_SLUG&envDescription=Public%20web%20origin,%20hosted%20API%20origin,%20and%20GitHub%20App%20slug";

const RENDER_DEPLOY_URL =
  process.env.NEXT_PUBLIC_RENDER_DEPLOY_URL ??
  "https://render.com/deploy?repo=https://github.com/the-niresh/plug-and-play-reviewer";

const RAILWAY_DEPLOY_URL =
  process.env.NEXT_PUBLIC_RAILWAY_DEPLOY_URL ??
  "https://railway.com/new/github.com/the-niresh/plug-and-play-reviewer";

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
    kicker: "01",
    title: "GitHub PR",
    body: "The GitHub App receives the pull request event and the head SHA.",
  },
  {
    kicker: "02",
    title: "hosted job",
    body: "The control plane stores job metadata only. It does not receive the diff.",
  },
  {
    kicker: "03",
    title: "local runner",
    body: "Your runner claims the job, fetches the patch, and keeps the source local.",
  },
  {
    kicker: "04",
    title: "retrieval",
    body: "Repo chunks join the packed diff before the model call.",
  },
  {
    kicker: "05",
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
  { id: "how-a-review-moves", kicker: "01", title: "How a review moves" },
  { id: "hosted-vs-local", kicker: "02", title: "Hosted vs local" },
  { id: "what-already-works", kicker: "03", title: "What already works" },
  { id: "what-teams-can-change", kicker: "04", title: "What teams can change" },
  { id: "what-the-evals-show", kicker: "05", title: "What the evals show" },
  { id: "how-to-set-it-up", kicker: "06", title: "How to set it up" },
] as const;

export default function HomePage() {
  return (
    <div className="landing-root">
      <a
        href="#how-a-review-moves"
        className="bg-primary text-primary-foreground focus:ring-ring absolute left-4 z-50 -translate-y-[120%] px-3 py-2 text-sm focus:translate-y-4 focus:ring-2 focus:outline-none"
      >
        Skip to how a review moves
      </a>
      <SiteNav />
      <main className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <section className="border-border grid gap-10 border-b py-14 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:items-end lg:gap-14 lg:py-20">
          <div className="min-w-0">
            <p className="landing-kicker">{PRODUCT_NAME}</p>
            <p className="text-muted-foreground mt-4 font-mono text-xs tracking-wide uppercase">
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
            <div className="mt-10 flex flex-col gap-4">
              <a
                href={SIGN_IN_URL}
                className={cn(buttonVariants({ size: "lg" }), "w-fit gap-2")}
              >
                <GithubMark className="size-4" />
                Sign in with GitHub
              </a>
              <div className="grid grid-cols-1 gap-3 sm:flex sm:flex-wrap sm:items-center">
                <a
                  href={VERCEL_DEPLOY_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="landing-link inline-flex items-center gap-1.5 text-sm"
                >
                  <VercelMark className="size-3.5" />
                  Deploy frontend on Vercel
                </a>
                <a
                  href={RENDER_DEPLOY_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="landing-link inline-flex items-center gap-1.5 text-sm"
                >
                  <RenderMark className="size-3.5" />
                  Deploy API on Render
                </a>
                <a
                  href={RAILWAY_DEPLOY_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="landing-link inline-flex items-center gap-1.5 text-sm"
                >
                  <RailwayMark className="size-3.5" />
                  Deploy API on Railway
                </a>
              </div>
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
          <p className="landing-kicker">{SECTIONS[0].kicker}</p>
          <h2 className="landing-display landing-section-title mt-2 font-semibold">
            {SECTIONS[0].title}
          </h2>
          <p className="text-muted-foreground mt-4 max-w-prose text-base leading-relaxed">
            GitHub PR to hosted job to local runner to retrieval to review comment. The
            hosted box never holds the patch.
          </p>
          <ol className="mt-10 grid gap-0 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1.2fr]">
            {FLOW_STEPS.map((step, index) => (
              <li
                key={step.kicker}
                className={cn(
                  "border-border min-w-0 border-t px-0 py-5",
                  "lg:border-t-0 lg:border-l lg:px-4 lg:first:border-l-0 lg:first:pl-0",
                  index > 0 && "lg:pt-0",
                )}
              >
                <p className="landing-kicker text-[11px]">{step.kicker}</p>
                <h3 className="mt-3 font-mono text-sm font-semibold">{step.title}</h3>
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
          <p className="landing-kicker">{SECTIONS[1].kicker}</p>
          <h2 className="landing-display landing-section-title mt-2 font-semibold">
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
                    <dt className="text-warning text-[11px] font-medium tracking-wide uppercase">
                      Hosted
                    </dt>
                    <dd className="text-muted-foreground mt-1">{row.hosted}</dd>
                  </div>
                  <div>
                    <dt className="text-success text-[11px] font-medium tracking-wide uppercase">
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
                  <th scope="col" className="text-warning px-4 py-3 font-medium">
                    Hosted
                  </th>
                  <th scope="col" className="text-success px-4 py-3 font-medium">
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
          <p className="landing-kicker">{SECTIONS[2].kicker}</p>
          <h2 className="landing-display landing-section-title mt-2 font-semibold">
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
            <p className="landing-kicker">{SECTIONS[3].kicker}</p>
            <h2 className="landing-display mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
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
            <p className="landing-kicker">Access shape</p>
            <h2 className="landing-display mt-2 text-2xl font-semibold tracking-tight">
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
          <p className="landing-kicker">{SECTIONS[4].kicker}</p>
          <h2 className="landing-display landing-section-title mt-2 font-semibold">
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
            <p className="landing-kicker">{SECTIONS[5].kicker}</p>
            <h2 className="landing-display landing-section-title mt-2 font-semibold">
              {SECTIONS[5].title}
            </h2>
            <ol className="mt-8 flex flex-col gap-3">
              {SETUP_STEPS.map((step, index) => (
                <li
                  key={step.title}
                  className="border-border border-t px-0 py-4 first:border-t-0 first:pt-0"
                >
                  <p className="font-mono text-sm font-semibold">
                    {String(index + 1).padStart(2, "0")}  {step.title}
                  </p>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                    {step.body}
                  </p>
                </li>
              ))}
            </ol>
            <p className="text-muted-foreground mt-5 max-w-prose text-sm leading-relaxed">
              One-click Render still needs your own secrets and database.
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
            <p className="landing-kicker">07</p>
            <h2 className="landing-display mt-2 text-xl font-semibold tracking-tight">
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
