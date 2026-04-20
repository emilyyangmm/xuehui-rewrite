import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 30;

export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");
  if (!token) return NextResponse.json({ status: "error", error: "缺少token" });

  try {
    const res = await fetch(
      `https://sso.douyin.com/check_qrconnect/?token=${token}&service=https%3A%2F%2Fwww.douyin.com&need_logo=false&device_platform=web_app&aid=6383&account_sdk_source=sso&sdk_version=2.2.5-rc.6`,
      {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Referer": "https://www.douyin.com/",
          "Accept": "application/json, text/plain, */*",
        },
        cache: "no-store",
        redirect: "manual",
      }
    );

    const data = await res.json();
    const status = data?.data?.status;

    // status: 1=待扫码 2=已扫码 3=已确认 4=已过期
    if (status === 3) {
      const redirectUrl = data.data?.redirect_url;
      if (redirectUrl) {
        // 跟随跳转，从响应头捕获 Set-Cookie
        const loginRes = await fetch(redirectUrl, {
          headers: {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          },
          redirect: "follow",
          cache: "no-store",
        });
        // 从响应头收集所有 Set-Cookie
        const setCookies = loginRes.headers.getSetCookie?.() ?? [];
        const cookieMap: Record<string, string> = {};
        for (const c of setCookies) {
          const part = c.split(";")[0].trim();
          const idx = part.indexOf("=");
          if (idx > 0) {
            const k = part.slice(0, idx).trim();
            const v = part.slice(idx + 1).trim();
            if (k && v) cookieMap[k] = v;
          }
        }
        const cookieStr = Object.entries(cookieMap).map(([k, v]) => `${k}=${v}`).join("; ");
        return NextResponse.json({ status: "done", cookie: cookieStr });
      }
      return NextResponse.json({ status: "done", cookie: "" });
    } else if (status === 4) {
      return NextResponse.json({ status: "expired" });
    } else if (status === 2) {
      return NextResponse.json({ status: "scanned" });
    } else {
      return NextResponse.json({ status: "waiting" });
    }
  } catch (e: any) {
    return NextResponse.json({ status: "error", error: e.message });
  }
}
