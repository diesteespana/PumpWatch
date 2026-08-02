import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_APP_NAME: "PumpWatch",
    NEXT_PUBLIC_APP_DOMAIN: "pumpwat.ch",
  },
};

export default nextConfig;
