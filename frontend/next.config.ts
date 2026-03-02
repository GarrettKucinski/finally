import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/api/stream/:path*",
        headers: [
          {
            key: "X-Accel-Buffering",
            value: "no",
          },
          {
            key: "Cache-Control",
            value: "no-store",
          },
          {
            key: "Content-Type",
            value: "text/event-stream",
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
