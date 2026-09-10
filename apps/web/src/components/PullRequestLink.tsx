type PullRequestLinkProps = {
  url: string | null;
};

/** External link to the GitHub pull request a hosted review came from. */
export function PullRequestLink({ url }: PullRequestLinkProps) {
  if (!url) {
    return null;
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-foreground relative z-10 rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      Open PR
    </a>
  );
}
