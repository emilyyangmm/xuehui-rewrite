import { NextRequest, NextResponse } from "next/server";
const API = "https://u946450-a783-20029e21.westc.seetacloud.com:8443";

export async function GET() {
  try {
    const res = await fetch(`${API}/machine-code`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
