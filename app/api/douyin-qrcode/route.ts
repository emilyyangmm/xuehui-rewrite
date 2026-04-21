export const runtime = 'edge';
import { NextResponse } from "next/server";

export const maxDuration = 30;

export async function GET() {
  try {
    const res = await fetch(
      "https://sso.douyin.com/get_qrcode/?service=https%3A%2F%2Fwww.douyin.com&need_logo=false&need_short_url=true&device_platform=web_app&aid=6383&account_sdk_source=sso&sdk_version=2.2.5-rc.6&language=zh",
      {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Referer": "https://www.douyin.com/",
          "Accept": "application/json, text/plain, */*",
        },
        cache: "no-store",
      }
    );
    const text = await res.text();
    let data: any;
    try { data = JSON.parse(text); } catch {
      return NextResponse.json({ error: "抖音接口返回异常：" + text.slice(0, 100) }, { status: 500 });
    }
    if (!data?.data?.token) {
      return NextResponse.json({ error: "获取二维码失败" }, { status: 500 });
    }
    return NextResponse.json({
      token: data.data.token,
      qrcode_url: data.data.qrcode_index_url,
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
