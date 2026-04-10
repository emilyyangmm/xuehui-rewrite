import { NextRequest, NextResponse } from "next/server";
const API = "https://u946450-hvp3-093d8faa.westd.seetacloud.com:8443";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${API}/verify-license`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activation_code: body.activation_code }),
    });
    const data = await res.json();
    return NextResponse.json({ valid: data.success, ...data });
  } catch (e: any) {
    return NextResponse.json({ valid: false, error: e.message }, { status: 500 });
  }
}
