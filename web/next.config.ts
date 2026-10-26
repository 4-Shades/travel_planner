import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // The app's own folder, so lockfiles elsewhere on the machine are not mistaken for its root.
  turbopack: { root: process.cwd() },
};

export default nextConfig;
