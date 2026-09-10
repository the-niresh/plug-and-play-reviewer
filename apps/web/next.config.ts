import type { NextConfig } from "next";

function normalizeOrigin(value: string | undefined): string | null {
  if (!value) {
    return null;
  }
  return value.replace(/\/+$/, "");
}

const controlPlaneOrigin = normalizeOrigin(process.env.NEXT_PUBLIC_CONTROL_PLANE_ORIGIN);

const nextConfig: NextConfig = {
  // next build writes hashed chunks into .next. next dev writes unhashed
  // page.js. Sharing one folder makes __webpack_modules__[moduleId] is not
  // a function. Dev keeps its own cache.
  distDir: process.env.NODE_ENV === "production" ? ".next" : ".next-dev",
  async rewrites() {
    if (!controlPlaneOrigin) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${controlPlaneOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
