import { NextRequest, NextResponse } from "next/server";
const API = "https://u946450-hvp3-093d8faa.westd.seetacloud.com:8443";

export async function GET() {
  try {
    const res = await fetch(`${API}/machine-code`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
