import type { NextConfig } from "next";

// BACKEND_URL is set in Vercel project settings (or .env.local for local dev).
// Falls back to localhost for local docker-compose usage.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: require("path").join(__dirname, "../"),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
