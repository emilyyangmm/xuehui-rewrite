import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const backendUrl = (req.headers.get("X-Backend-URL") || "").replace(/\/$/, "");
    const endpoint = req.headers.get("X-Endpoint") || "";
    if (!backendUrl) return NextResponse.json({ error: "未设置服务器地址" }, { status: 400 });
    if (!endpoint) return NextResponse.json({ error: "缺少endpoint" }, { status: 400 });

    const ct = req.headers.get("content-type") || "";
    const body = ct.includes("multipart") ? await req.arrayBuffer() : await req.text();

    const fwdHeaders: Record<string, string> = { "Content-Type": ct };
    const qwenKey = req.headers.get("X-Qwen-Key");
    if (qwenKey) fwdHeaders["X-Qwen-Key"] = qwenKey;

    const res = await fetch(`${backendUrl}/${endpoint}`, {
      method: "POST",
      headers: fwdHeaders,
      body: body as any,
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
