import { GithubMark } from "@/components/github-mark";
import { ProductStage } from "@/components/landing/ProductStage";
import { SiteNav } from "@/components/SiteNav";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ReviewFinding } from "@/lib/reviews";

export const metadata = {
  title: "PR Reviewer",
  description:
    "Private AI code review. Hosted jobs, a local runner, and your model key.",
};

const SIGN_IN_URL = "/api/auth/github/sign-in?return_to=/dashboard";

const RENDER_DEPLOY_URL =
  process.env.NEXT_PUBLIC_RENDER_DEPLOY_URL ??
  "https://render.com/deploy?repo=https://github.com/the-niresh/plug-and-play-reviewer";

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
    body: "The model call happens on your laptop or server. Source never goes to the hosted site.",
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
  { item: "Model key", hosted: "Never", local: "Yes, in the local key store" },
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
    body: "Point the runner at the hosted URL. reviewer.niresh.tech is the live control plane.",
  },
  {
    title: "Local runner",
    body: "Install the runner on the machine that may see your source.",
  },
  {
    title: "Model key",
    body: "Keep the model key on the runner. It never goes to the hosted database.",
  },
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
      <main className="mx-auto w-full max-w-6xl px-6">
        <section className="border-border grid gap-10 border-b py-[var(--space-section)] lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-end">
          <div className="min-w-0">
            <p className="text-primary font-mono text-xs tracking-[0.2em] uppercase">
              PR Reviewer
            </p>
            <h1 className="landing-display mt-5 max-w-[18ch] text-5xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-6xl">
              Private AI code review that stays on your machine
            </h1>
            <p className="text-muted-foreground mt-6 max-w-prose text-lg leading-relaxed">
              This is an open source PR reviewer. A hosted control plane takes GitHub
              events. The local runner reads the diff and calls your model.
            </p>
            <p className="text-muted-foreground mt-4 max-w-prose leading-relaxed">
              Use it for AI code review self hosted on a laptop or a server you run.
              Teams who need a CodeRabbit alternative keep diffs on their own runner.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <a
                href={RENDER_DEPLOY_URL}
                className={cn(buttonVariants({ size: "lg" }), "gap-2")}
              >
                Deploy on Render
              </a>
              <a
                href={SIGN_IN_URL}
                className={cn(buttonVariants({ size: "lg", variant: "outline" }), "gap-2")}
              >
                <GithubMark className="size-4" />
                Sign in with GitHub
              </a>
            </div>
            <a
              href="#how-a-review-moves"
              className="text-primary mt-6 inline-block text-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 rounded-sm focus-visible:ring-[3px] focus-visible:outline-none"
            >
              See how a review moves
            </a>
          </div>
          <ProductStage finding={EXAMPLE_FINDING} />
        </section>

        <section
          id="how-a-review-moves"
          className="border-border border-b py-[var(--space-section)]"
        >
          <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
            02
          </p>
          <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
            How a review moves
          </h2>
          <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
            GitHub PR to hosted job to local runner to retrieval to review comment.
            The hosted box never holds the patch.
          </p>
          <ol className="mt-8 flex gap-px overflow-x-auto border">
            {FLOW_STEPS.map((step) => (
              <li
                key={step.kicker}
                className="bg-card min-w-[12.5rem] flex-1 px-4 py-4"
              >
                <p className="text-primary font-mono text-[11px] tracking-[0.14em] uppercase">
                  {step.kicker}
                </p>
                <h3 className="mt-2 font-mono text-sm font-medium">{step.title}</h3>
                <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section
          id="hosted-vs-local"
          className="border-border border-b py-[var(--space-section)]"
        >
          <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
            03
          </p>
          <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
            Hosted vs local
          </h2>
          <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
            This is private AI code review. Source, diffs, and the model key stay on
            the runner. Finding text may sit on the dashboard so you can read it.
          </p>
          <div className="mt-8 overflow-x-auto border">
            <table className="w-full min-w-[36rem] border-collapse text-sm">
              <caption className="sr-only">
                What the hosted control plane sees versus what stays on the local runner
              </caption>
              <thead>
                <tr className="bg-muted/40 text-muted-foreground text-left">
                  <th scope="col" className="px-4 py-2.5 font-medium">
                    Data
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-medium">
                    Hosted
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-medium">
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
          className="border-border border-b py-[var(--space-section)]"
        >
          <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
            04
          </p>
          <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
            What already works
          </h2>
          <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
            These are the hard parts. Grounded findings, suggestion blocks, and the
            human gate are product rules, not slogans.
          </p>
          <dl className="mt-8 border">
            {PRIDE.map((item) => (
              <div
                key={item.title}
                className="border-border grid gap-2 border-b px-4 py-4 last:border-b-0 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-8"
              >
                <dt className="font-mono text-sm font-medium">{item.title}</dt>
                <dd className="text-muted-foreground text-sm leading-relaxed">
                  {item.body}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <section
          id="what-teams-can-change"
          className="border-border grid gap-12 border-b py-[var(--space-section)] lg:grid-cols-2"
        >
          <div>
            <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
              05
            </p>
            <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
              What teams can change
            </h2>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              You can add agents and edit prompts per repository. Those settings stay
              private to that repo.
            </p>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              Repo A never receives Repo B prompts. This is permissioned team power,
              not a public dump.
            </p>
          </div>
          <div>
            <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
              06
            </p>
            <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
              What stays free and what is for teams
            </h2>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              A single person running a local reviewer can stay on a simple path.
            </p>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              Team controls, shared prompts, and extra repositories are the paid path.
            </p>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              There are no prices on this page. Team access is a later product rule,
              not a checkout form.
            </p>
          </div>
        </section>

        <section
          id="what-the-evals-show"
          className="border-border border-b py-[var(--space-section)]"
        >
          <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
            07
          </p>
          <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
            What the evals show
          </h2>
          <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
            Dev evals exist as working notes. They are not a baseline.
          </p>
          <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
            The scorecard page refuses a number until a measured run exists. Do not
            quote an internal note as a launch score.
          </p>
          <a
            href="/scorecard"
            className="text-primary mt-5 inline-block text-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 rounded-sm focus-visible:ring-[3px] focus-visible:outline-none"
          >
            Open the scorecard
          </a>
        </section>

        <section
          id="how-to-set-it-up"
          className="border-border grid gap-12 border-b py-[var(--space-section)] lg:grid-cols-2"
        >
          <div>
            <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
              08
            </p>
            <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
              How to set it up
            </h2>
            <ol className="mt-6 border">
              {SETUP_STEPS.map((step, index) => (
                <li
                  key={step.title}
                  className="border-border border-b px-4 py-4 last:border-b-0"
                >
                  <p className="font-mono text-sm font-medium">
                    {String(index + 1).padStart(2, "0")}  {step.title}
                  </p>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                    {step.body}
                  </p>
                </li>
              ))}
            </ol>
            <p className="text-muted-foreground mt-4 max-w-prose text-sm leading-relaxed">
              One-click Render or Railway still needs your own secrets and database.
            </p>
          </div>
          <div>
            <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
              09
            </p>
            <h2 className="landing-display mt-2 text-3xl font-semibold tracking-tight">
              What is not automatic yet
            </h2>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              The reviewer does not learn from human replies yet.
            </p>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              Public scorecard publishing is still refused. Do not treat internal eval
              notes as a launch number.
            </p>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              An empty-generate retry exists but stays off. It raised false findings
              when we tried it.
            </p>
          </div>
        </section>

        <footer className="text-muted-foreground py-8 font-mono text-xs">
          PR Reviewer · reviewer.niresh.tech
        </footer>
      </main>
    </div>
  );
}
