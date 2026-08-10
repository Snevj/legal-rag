import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  agentRules: false,
  // Bundles only the production deps actually needed at runtime into
  // .next/standalone - keeps the Docker image lean instead of shipping the
  // full node_modules tree.
  output: "standalone",
};

export default nextConfig;
