import Link from "next/link";

import { CommandLine } from "@/components/CommandLine";
import { LogoBadge } from "@/components/Logo";
import { SiteNav } from "@/components/SiteNav";
import { pageTitle, siteHost } from "@/lib/site";

export const metadata = {
  title: pageTitle("Docs"),
  description:
    "Install the runner, connect GitHub, add a model key, and start reviewing pull requests.",
  alternates: { canonical: "/docs" },
};

const REPO_DOCS = "https://github.com/the-niresh/plug-and-play-reviewer/blob/main/docs";

const SECTIONS = [
  {
    tag: "Install",
    title: "Install the runner",
    body: [
      "The runner is the program on your machine that reads pull requests and calls the model.",
      "Install uv first, then run the install script from the public repository.",
      "The script checks a checksum before it copies files. If the checksum fails, the install stops.",
    ],
    commands: [
      `curl -fsSL https://${siteHost()}/install | sh`,
      "reviewer --help",
    ],
    docHref: `${REPO_DOCS}/INSTALL.md`,
    docLabel: "Full install guide",
  },
  {
    tag: "GitHub connect",
    title: "Connect GitHub",
    body: [
      "Run setup with your hosted origin. The terminal UI walks you through GitHub App approval.",
      "Pick the repositories the App may read. Without GitHub, no review can start.",
    ],
    commands: [
      `reviewer setup --hosted-origin https://${siteHost()}`,
      "reviewer doctor",
      "reviewer start",
    ],
    docHref: `${REPO_DOCS}/SELF_HOSTING.md`,
    docLabel: "Self hosting walkthrough",
  },
  {
    tag: "Bring your own key",
    title: "Add your model key",
    body: [
      "A model key is an API key from OpenAI, Anthropic, or another provider you choose.",
      "Setup collects it with hidden input. Keys stay in your OS keychain, or in a local file if no keychain exists.",
      "A model key never goes to the hosted database.",
    ],
    commands: [
      `reviewer setup --hosted-origin https://${siteHost()}`,
      "reviewer status",
    ],
    docHref: `${REPO_DOCS}/INSTALL.md#setup`,
    docLabel: "Setup section in INSTALL.md",
  },
  {
    tag: "agent plugin",
    title: "Use it from another agent",
    body: [
      "The same review is available through MCP, a JSON CLI, ACP, and A2A.",
      "One core backs all four surfaces. A parity test keeps them aligned.",
    ],
    commands: [
      "reviewer agent-json review --owner OWNER --repository REPO --pull-request N",
      "reviewer agent-json findings --review-id ID",
      "reviewer agent-json remediation-prompts --review-id ID",
    ],
    docHref: `${REPO_DOCS}/AGENT_CONTRACT.md`,
    docLabel: "Agent contract",
  },
] as const;

export default function DocsPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto w-full max-w-3xl px-6 py-14">
        <header className="flex items-start gap-4">
          <LogoBadge className="size-12 shrink-0" />
          <div className="min-w-0">
            <h1 className="text-3xl font-semibold tracking-tight">Docs</h1>
            <p className="text-muted-foreground mt-3 max-w-prose leading-relaxed">
              How to install the runner and connect GitHub. Read this in order, then open
              the repo docs for depth.
            </p>
          </div>
        </header>
        <div className="mt-12 flex flex-col">
          {SECTIONS.map((section) => (
            <section
              key={section.tag}
              className="border-t py-8 first:border-t-0 first:pt-0"
            >
              <p className="section-label">{section.tag}</p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight">{section.title}</h2>
              <div className="text-muted-foreground mt-3 max-w-prose space-y-2 text-sm leading-relaxed">
                {section.body.map((sentence) => (
                  <p key={sentence}>{sentence}</p>
                ))}
              </div>
              <ul className="mt-5 flex flex-col gap-2">
                {section.commands.map((command) => (
                  <li key={command}>
                    <CommandLine command={command} />
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex flex-wrap gap-4">
                <a
                  href={section.docHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground inline-block rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
                >
                  {section.docLabel}
                </a>
                {section.tag === "agent plugin" ? (
                  <Link
                    href="/docs/agents"
                    className="text-foreground inline-block rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
                  >
                    See the four surfaces
                  </Link>
                ) : null}
              </div>
            </section>
          ))}
        </div>
      </main>
    </>
  );
}
