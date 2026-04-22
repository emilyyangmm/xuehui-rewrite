import { NextRequest, NextResponse } from "next/server";

const API = process.env.BACKEND_URL || "https://u946450-a783-20029e21.westc.seetacloud.com:8443";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { video_url, cookie } = body;
    if (!video_url) return NextResponse.json({ error: "缺少video_url" }, { status: 400 });

    const res = await fetch(`${API}/fetch-video`, {
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
