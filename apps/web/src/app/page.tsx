import { GithubMark } from "@/components/github-mark";
import { SiteNav } from "@/components/SiteNav";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Same relative path SignInPrompt uses (DashboardState.tsx).
const SIGN_IN_URL = "/api/auth/github/sign-in?return_to=/dashboard";

const RENDER_DEPLOY_URL =
  process.env.NEXT_PUBLIC_RENDER_DEPLOY_URL ??
  "https://render.com/deploy?repo=https://github.com/the-niresh/plug-and-play-reviewer";

const PILLARS = [
  {
    title: "Runs on your machine",
    body: "The review runs on your laptop or server. Your source code and diffs stay there.",
  },
  {
    title: "Works with humans and agents",
    body: "Use the terminal, the web dashboard, or MCP, CLI, ACP, and A2A from another agent.",
  },
  {
    title: "Free to use",
    body: "It costs nothing to run. Install it and use it.",
  },
] as const;

export default function HomePage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto w-full max-w-5xl px-6">
        <section className="border-b py-[var(--space-section)]">
          <span className="text-primary font-mono text-xs tracking-[0.2em] uppercase">
            pr-reviewer
          </span>
          <h1 className="mt-5 max-w-[20ch] text-5xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-6xl lg:text-7xl">
            Review pull requests on your machine
          </h1>
          <p className="text-muted-foreground mt-6 max-w-prose text-lg leading-relaxed">
            A runner on your machine reads the diff and calls the model. The hosted site
            shows findings and cost. It never sees your source, your diffs, or your model
            key.
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
        </section>

        <section className="grid gap-px border-x-0 py-[var(--space-section)] sm:grid-cols-3 sm:gap-8">
          {PILLARS.map((pillar) => (
            <article
              key={pillar.title}
              className="sm:border-l sm:pl-6 sm:first:border-l-0 sm:first:pl-0"
            >
              <h2 className="text-base font-semibold">{pillar.title}</h2>
              <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                {pillar.body}
              </p>
            </article>
          ))}
        </section>

        <footer className="text-muted-foreground border-t py-8 font-mono text-xs">
          reviewer.niresh.tech
        </footer>
      </main>
    </>
  );
}
