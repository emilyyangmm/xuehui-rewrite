import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "薛辉改写工具",
  description: "抖音视频拉取、薛辉改写、数字人生成一体化平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
