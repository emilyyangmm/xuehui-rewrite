import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const backendUrl = (req.headers.get("X-Backend-URL") || "").replace(/\/$/, "");
    if (!backendUrl) return NextResponse.json({ error: "未设置服务器地址" }, { status: 400 });
    const body = await req.json();
    const { video_url, cookie } = body;
    if (!video_url) return NextResponse.json({ error: "缺少video_url" }, { status: 400 });

    const res = await fetch(`${backendUrl}/fetch-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: video_url, cookie }),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
