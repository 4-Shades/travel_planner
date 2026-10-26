import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // The container image runs the self-contained server that this produces (see Dockerfile).
  output: process.env.NEXT_STANDALONE === "1" ? "standalone" : undefined,
  // The app's own folder, so lockfiles elsewhere on the machine are not mistaken for its root.
  turbopack: { root: process.cwd() },
};

export default nextConfig;
