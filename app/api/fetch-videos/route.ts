import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "https://u946450-b2d1-6dbf3f52.westc.seetacloud.com:8443";

export async function POST(request: NextRequest) {
  try {
    const { url, sortBy } = await request.json();
    
    if (!url) {
      return NextResponse.json({ success: false, error: "请提供抖音链接" }, { status: 400 });
    }
    
    // 调用后端获取用户视频
    const res = await fetch(`${BACKEND_URL}/user-videos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, sort_by: sortBy || "play" }),
    });
    
    if (!res.ok) {
      return NextResponse.json({ success: false, error: `后端调用失败: ${res.status}` }, { status: 500 });
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
