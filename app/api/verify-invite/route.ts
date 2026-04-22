import { NextRequest, NextResponse } from "next/server";

const API = process.env.BACKEND_URL || "https://u946450-a783-20029e21.westc.seetacloud.com:8443";

export async function POST(req: NextRequest) {
  try {
    const { code } = await req.json();
    if (!code) {
      return NextResponse.json({ success: false, message: "请输入邀请码" }, { status: 400 });
    }
    
    const res = await fetch(`${API}/invite/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code.trim() }),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ success: false, message: e.message }, { status: 500 });
  }
}
