import { ImageResponse } from "next/og";

import { PRODUCT_NAME } from "@/lib/site";

export const alt = PRODUCT_NAME;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

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
        <div style={{ display: "flex", fontSize: 22, letterSpacing: "0.28em" }}>
          PR REVIEWER
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
          reviewer.niresh.tech
        </div>
      </div>
    ),
    { ...size },
  );
}
