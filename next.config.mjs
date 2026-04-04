/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['*.dev.coze.site', '130.211.240.194'],
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lf-coze-web-cdn.coze.cn',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'p3-pc-sign.douyinpic.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '*.douyinpic.com',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
