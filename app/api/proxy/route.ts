import { NextRequest, NextResponse } from "next/server";

async function handle(req: NextRequest) {
  try {
    const backendUrl = (req.headers.get("X-Backend-URL") || "").replace(/\/$/, "");
    const endpoint = req.headers.get("X-Endpoint") || "";
    if (!backendUrl) return NextResponse.json({ error: "未设置服务器地址" }, { status: 400 });
    if (!endpoint) return NextResponse.json({ error: "缺少endpoint" }, { status: 400 });

    const fwdHeaders: Record<string, string> = {};
    const qwenKey = req.headers.get("X-Qwen-Key");
    if (qwenKey) fwdHeaders["X-Qwen-Key"] = qwenKey;

    let body: any = undefined;
    if (req.method === "POST") {
      const ct = req.headers.get("content-type") || "";
      fwdHeaders["Content-Type"] = ct;
      body = ct.includes("multipart") ? await req.arrayBuffer() : await req.text();
    }

    const res = await fetch(`${backendUrl}/${endpoint}`, {
      method: req.method,
      headers: fwdHeaders,
      body,
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}

export const GET = handle;
export const POST = handle;
