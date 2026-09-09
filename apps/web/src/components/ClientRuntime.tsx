"use client";

import Link from "next/link";

/** Client child for the root layout.
 *
 * Next 15 webpack leaves __webpack_require__.n out of webpack.js when the
 * first page is server components only. DashboardShell then dies on
 * import Link from "next/link". This file uses that same default import
 * so landing, docs, and scorecard first visits compile the helper. */
export function ClientRuntime() {
  return (
    <Link href="/" className="sr-only">
      PR Reviewer
    </Link>
  );
}
