import { NextResponse } from "next/server";

/** Serves the runner install script at a name a person can type and trust.
 *
 *  `curl -fsSL https://plugandplayreviewer.online/install | sh` instead of a raw
 *  githubusercontent URL nobody can read out loud. The script itself still lives in the
 *  repository, so there is one copy; this route relays it.
 *
 *  It relays rather than redirects on purpose. A redirect only works with curl -L, and
 *  someone who leaves that flag off would pipe an empty body straight into sh and see
 *  nothing happen at all. */

const SOURCE =
  "https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh";

const CACHE_SECONDS = 300;

export const revalidate = 300;

/** Valid shell, so that a pipe into sh fails loudly instead of running half a page of
 *  HTML. Without -f curl hands the error body to the shell regardless of status code. */
const UNAVAILABLE = [
  "#!/bin/sh",
  'echo "Could not fetch the installer. Try the source directly:" >&2',
  `echo "  curl -fsSL ${SOURCE} | sh" >&2`,
  "exit 1",
  "",
].join("\n");

export async function GET() {
  let script: string;
  try {
    const upstream = await fetch(SOURCE, { next: { revalidate: CACHE_SECONDS } });
    if (!upstream.ok) {
      return shell(UNAVAILABLE, 502);
    }
    script = await upstream.text();
  } catch {
    return shell(UNAVAILABLE, 502);
  }
  return shell(script, 200);
}

function shell(body: string, status: number): NextResponse {
  return new NextResponse(body, {
    status,
    headers: {
      "content-type": "text/x-shellscript; charset=utf-8",
      "cache-control":
        status === 200 ? `public, max-age=${CACHE_SECONDS}` : "no-store",
    },
  });
}
