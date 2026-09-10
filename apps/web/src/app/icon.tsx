import { ImageResponse } from "next/og";

/** Favicon.
 *
 *  This file is a Next.js **metadata route**, not a component: it must return a Response
 *  (an ImageResponse), and it is rendered by Satori at build time, so Tailwind classes and
 *  `currentColor` do nothing here. Every colour and size is inline and literal on purpose.
 *  Returning JSX instead broke `next build` with "No response is returned from route
 *  handler", which type-checking cannot catch.
 *
 *  Simplified mark: lens, bug body, two spots. No legs, antennae or git trunk, because
 *  none of that survives at 32px. The full mark lives in components/Logo.tsx. */

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#1c1f27",
          borderRadius: 6,
        }}
      >
        <svg
          width="26"
          height="26"
          viewBox="0 0 32 32"
          fill="none"
          stroke="#f2f3f5"
          strokeWidth={2.4}
          strokeLinecap="round"
        >
          <circle cx="15" cy="14" r="8.5" />
          <path d="M21.2 20.2L26 25" strokeWidth={3} />
          <ellipse cx="15" cy="15" rx="3.1" ry="3.7" fill="#E5484D" stroke="#f2f3f5" />
          <circle cx="13.9" cy="14.1" r="0.75" fill="#1F1F1F" stroke="none" />
          <circle cx="16.1" cy="16.1" r="0.75" fill="#1F1F1F" stroke="none" />
        </svg>
      </div>
    ),
    { ...size },
  );
}
