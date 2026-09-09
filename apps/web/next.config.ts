import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // next build writes hashed chunks into .next. next dev writes unhashed
  // page.js. Sharing one folder makes __webpack_modules__[moduleId] is not
  // a function. Dev keeps its own cache.
  distDir: process.env.NODE_ENV === "production" ? ".next" : ".next-dev",
};

export default nextConfig;
