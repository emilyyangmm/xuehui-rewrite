import { NextRequest, NextResponse } from "next/server";

const API = "https://u946450-b29a-1d68bd35.westd.seetacloud.com:8443";
const QWEN_KEY = process.env.QWEN_API_KEY || "";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${API}/rewrite`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Qwen-Key": QWEN_KEY,
      },
      body: JSON.stringify({ text: body.text }),
    });
    const data = await res.json();
    // 兼容前端期望的格式
    return NextResponse.json({
      success: true,
      result: {
        script: data.result || "",
        topics: [],
      }
    });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
