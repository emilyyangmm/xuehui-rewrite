import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 30;

export async function POST(req: NextRequest) {
  try {
    const { aweme_id, cookie } = await req.json();
    if (!aweme_id) return NextResponse.json({ error: "缺少视频ID" }, { status: 400 });

    // 尝试多个接口，依次降级
    const endpoints = [
      `https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=${aweme_id}`,
      `https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${aweme_id}&aid=6383&device_platform=webapp`,
    ];

    let playUrl = "";
    let title = "";
    let lastError = "";

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint, {
          headers: {
            Cookie: cookie || "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            Referer: "https://www.douyin.com/",
            Accept: "application/json, text/plain, */*",
            "Accept-Encoding": "identity",
          },
          cache: "no-store",
        });
        const text = await res.text();
        if (!text.trim()) { lastError = `${endpoint} 返回空响应`; continue; }
        let data: any;
        try { data = JSON.parse(text); } catch { lastError = `${endpoint} 返回非JSON: ${text.slice(0, 80)}`; continue; }

        // iesdouyin 格式
        const detail = data?.aweme_detail ?? data?.item_list?.[0];
        if (!detail) { lastError = `${endpoint} 无视频数据`; continue; }

        const urls: string[] = detail?.video?.play_addr?.url_list ?? detail?.video?.download_addr?.url_list ?? [];
        playUrl = urls.find((u: string) => u.startsWith("https")) || urls[0] || "";
        title = detail?.desc ?? "";
        if (playUrl) break;
      } catch (e: any) {
        lastError = e.message;
      }
    }

    if (!playUrl) return NextResponse.json({ error: `无法获取视频直链：${lastError}` }, { status: 400 });

    if (!playUrl) return NextResponse.json({ error: "无法获取视频直链" }, { status: 400 });

    return NextResponse.json({ play_url: playUrl, title });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
