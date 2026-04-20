import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 30;

export async function POST(req: NextRequest) {
  try {
    const { aweme_id, cookie } = await req.json();
    if (!aweme_id) return NextResponse.json({ error: "缺少视频ID" }, { status: 400 });

    const res = await fetch(
      `https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${aweme_id}&aid=6383&device_platform=webapp`,
      {
        headers: {
          Cookie: cookie || "",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          Referer: "https://www.douyin.com/",
          Accept: "application/json, text/plain, */*",
        },
        cache: "no-store",
      }
    );

    const data = await res.json();
    const detail = data?.aweme_detail;
    if (!detail) return NextResponse.json({ error: "视频不存在或无权限" }, { status: 404 });

    const playUrls: string[] = detail?.video?.play_addr?.url_list ?? [];
    const playUrl = playUrls.find((u: string) => u.startsWith("https")) || playUrls[0] || "";
    const title: string = detail?.desc ?? "";

    if (!playUrl) return NextResponse.json({ error: "无法获取视频直链" }, { status: 400 });

    return NextResponse.json({ play_url: playUrl, title });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
