import { ImageResponse } from "next/og";

import { PRODUCT_NAME, siteHost } from "@/lib/site";

export const alt = PRODUCT_NAME;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** Same simplified mark as icon.tsx, drawn inline for next/og. */
function OgMark() {
  return (
    <svg
      width="88"
      height="88"
      viewBox="0 0 32 32"
      fill="none"
      stroke="#f2f3f5"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="16" cy="14" r="9" />
      <path d="M22.5 20.5L27 25" strokeWidth={2.6} />
      <ellipse cx="16" cy="15.5" rx="3.2" ry="3.8" fill="#6ee7a8" stroke="none" />
      <circle cx="14.8" cy="14.5" r="0.75" fill="#1c1f27" stroke="none" />
      <circle cx="17.2" cy="16.5" r="0.75" fill="#1c1f27" stroke="none" />
    </svg>
  );
}

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#1c1f27",
          color: "#f2f3f5",
          padding: "64px 72px",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <OgMark />
          <div style={{ display: "flex", fontSize: 22, letterSpacing: "0.12em" }}>
            {PRODUCT_NAME.toUpperCase()}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              display: "flex",
              fontSize: 64,
              lineHeight: 1.05,
              fontFamily: "ui-serif, Georgia, serif",
              maxWidth: 900,
            }}
          >
            Private AI code review that stays on your machine
          </div>
          <div style={{ display: "flex", fontSize: 28, color: "#9aa3b2" }}>
            Hosted jobs. Local runner. Your model key.
          </div>
        </div>
        <div style={{ display: "flex", fontSize: 22, color: "#6ee7a8" }}>
          {siteHost()}
        </div>
      </div>
    ),
    { ...size },
  );
}
