/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "i8.amplience.net",
      },
    ],
  },
};

export default nextConfig;
