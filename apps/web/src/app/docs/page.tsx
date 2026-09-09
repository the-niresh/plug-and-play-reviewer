import Link from "next/link";

import { SiteNav } from "@/components/SiteNav";

export const metadata = {
  title: "Docs | PR Reviewer",
  description:
    "Install the runner, connect GitHub, add a model key, and use the agent plugin.",
};

const SECTIONS = [
  {
    tag: "Install",
    title: "Install the runner",
    body: [
      "The runner is the program on your machine that reads pull requests and calls the model.",
      "Run the install script from a release.",
      "The script checks a checksum before it copies files.",
      "If the checksum fails, the install stops.",
    ],
  },
  {
    tag: "GitHub connect",
    title: "Connect GitHub",
    body: [
      "Open the terminal UI.",
      "If GitHub is not connected, it shows a sign-in link.",
      "Approve the GitHub App.",
      "Pick the repositories it may read.",
      "Without GitHub, no review can start.",
    ],
  },
  {
    tag: "Bring your own key",
    title: "Add your model key",
    body: [
      "A model key is an API key from OpenAI, Anthropic, or another provider you choose.",
      "Add it in the terminal UI.",
      "Keys stay in your OS keychain, or in a local file if no keychain exists.",
      "A model key never goes to the hosted database.",
    ],
  },
  {
    tag: "agent plugin",
    title: "Use it from another agent",
    body: [
      "The same review is available through MCP, a JSON CLI, ACP, and A2A.",
      "One core backs all four surfaces.",
      "A parity test keeps them aligned.",
    ],
  },
] as const;

export default function DocsPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto w-full max-w-3xl px-6 py-14">
        <h1 className="text-3xl font-semibold tracking-tight">Docs</h1>
        <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
          How to install the runner and connect GitHub. Read this in order.
        </p>
        <div className="mt-12 flex flex-col">
          {SECTIONS.map((section) => (
            <section
              key={section.tag}
              className="border-t py-8 first:border-t-0 first:pt-0"
            >
              <p className="text-primary font-mono text-xs tracking-[0.14em] uppercase">
                {section.tag}
              </p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight">{section.title}</h2>
              <div className="text-muted-foreground mt-3 max-w-prose space-y-2 text-sm leading-relaxed">
                {section.body.map((sentence) => (
                  <p key={sentence}>{sentence}</p>
                ))}
              </div>
              {section.tag === "agent plugin" ? (
                <Link
                  href="/docs/agents"
                  className="text-primary mt-4 inline-block rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
                >
                  See the four surfaces
                </Link>
              ) : null}
            </section>
          ))}
        </div>
      </main>
    </>
  );
}
