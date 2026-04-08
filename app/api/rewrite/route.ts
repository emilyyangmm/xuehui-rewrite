import { NextRequest, NextResponse } from "next/server";
const API = "https://u946450-b29a-1d68bd35.westd.seetacloud.com:8443";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const qwenKey = req.headers.get("X-Qwen-Key") || process.env.QWEN_API_KEY || "";
    const res = await fetch(`${API}/rewrite`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Qwen-Key": qwenKey },
      body: JSON.stringify({ text: body.text }),
    });
    const data = await res.json();
    return NextResponse.json({ success: true, result: { script: data.result || "", topics: [] } });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
