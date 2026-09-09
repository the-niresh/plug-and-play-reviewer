# Security policy

The full control catalog and the tests behind each rule live in
[docs/SECURITY.md](docs/SECURITY.md). This page is the private reporting route
for strangers and for GitHub's security tab.

## Report privately

Use GitHub private vulnerability reporting:

https://github.com/the-niresh/plug-and-play-reviewer/security/advisories/new

If that link fails, open the repository on GitHub, go to **Security**, then
**Report a vulnerability**.

## What to report here

Send a private report when you believe you found:

- **Prompt injection**: pull request or comment text that makes the reviewer
  skip the human gate, post without approval, or exfiltrate runner secrets.
- **Data-boundary bugs**: source, diffs, model keys, or other private review
  data reaching the hosted plane or Neon when
  `control_plane/boundary.py` and [docs/DATA_BOUNDARIES.md](docs/DATA_BOUNDARIES.md)
  say they should not.

Include steps to reproduce, what you expected, and what happened. Redact live
model keys, runner credentials, and database URLs.

We read every report. We do not promise a fixed response time.

## What not to report here

Install trouble, pairing errors, dashboard bugs, and feature ideas belong in
[GitHub Issues](https://github.com/the-niresh/plug-and-play-reviewer/issues).
Use a public issue unless the bug is a security boundary failure.
