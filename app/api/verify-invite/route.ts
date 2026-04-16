import { NextRequest, NextResponse } from "next/server";

const VALID_CODES = [
  "xuehui2024",
  "studio2024",
  "free",
  "test",
];

export async function POST(req: NextRequest) {
  try {
    const { code } = await req.json();
    if (!code) {
      return NextResponse.json({ success: false, error: "请输入邀请码" }, { status: 400 });
    }
    
    if (VALID_CODES.includes(code.trim())) {
      return NextResponse.json({ success: true });
    }
    
    return NextResponse.json({ success: false, error: "邀请码无效" });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
