import { NextRequest, NextResponse } from "next/server";
const BACKEND_URL = process.env.BACKEND_URL || "https://u946450-b2d1-6dbf3f52.westc.seetacloud.com:8443";

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/machine-code`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ machine_code: "获取失败，请检查后端连接" });
  }
}
