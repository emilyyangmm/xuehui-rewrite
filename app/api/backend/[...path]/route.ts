import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  "https://u946450-a783-20029e21.westc.seetacloud.com:8443";

export const maxDuration = 60;

async function proxy(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const { path } = params;
  const target = new URL(path.join("/"), BACKEND_URL + "/");

  req.nextUrl.searchParams.forEach((v, k) => target.searchParams.set(k, v));

  const fwdHeaders: Record<string, string> = {};
  for (const key of ["content-type", "x-qwen-key", "x-douyin-cookie"]) {
    const val = req.headers.get(key);
    if (val) fwdHeaders[key] = val;
  }

  let body: ArrayBuffer | string | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("multipart/form-data")) {
      body = await req.arrayBuffer();
    } else {
      body = await req.text();
    }
  }

  const res = await fetch(target.toString(), {
    method: req.method,
    headers: fwdHeaders,
    body: body as any,
  });

  const ct = res.headers.get("content-type") || "";

  if (ct.includes("application/json")) {
    let text = await res.text();
    text = text.replaceAll(BACKEND_URL, "/api/backend");
    return new NextResponse(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new NextResponse(res.body, {
    status: res.status,
    headers: { "Content-Type": ct },
  });
}

export const GET = proxy;
export const POST = proxy;
