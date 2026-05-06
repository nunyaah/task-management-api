/** @type {import('next').NextConfig} */
const nextConfig = {
  // 'standalone' copies only the files needed to run the server into .next/standalone.
  // This lets the Docker runner stage copy a minimal set of files instead of
  // the full node_modules (which can be hundreds of MB).
  output: 'standalone',
}

export default nextConfig
