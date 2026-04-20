import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 30;

function extractSecUid(url: string): string {
  let m = url.match(/sec_uid=([\w-]+)/);
  if (m) return m[1];
  m = url.match(/\/user\/([\w-]+)/);
  if (m) return m[1];
  return "";
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { url, count = 20, sort_by = "play", cookie = "" } = body;

    const secUid = extractSecUid(url);
    if (!secUid) {
      return NextResponse.json({ error: "无法解析博主ID，请粘贴博主主页链接" }, { status: 400 });
    }

    const apiUrl = `https://www.douyin.com/aweme/v1/web/aweme/post/?device_platform=webapp&aid=6383&sec_user_id=${secUid}&count=${count}&max_cursor=0`;

    const res = await fetch(apiUrl, {
      headers: {
        Cookie: cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Referer: "https://www.douyin.com/",
        Accept: "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
      },
      cache: "no-store",
    });

    const data = await res.json();
    const videos = (data.aweme_list || []).map((v: any) => {
      const coverList = v?.video?.cover?.url_list ?? [];
      const stats = v?.statistics ?? {};
      return {
        aweme_id: v.aweme_id ?? "",
        title: (v.desc ?? "").slice(0, 80),
        cover: coverList[0] ?? "",
        likes: stats.digg_count ?? 0,
        comments: stats.comment_count ?? 0,
        shares: stats.share_count ?? 0,
        plays: stats.play_count ?? 0,
        video_url: `https://www.douyin.com/video/${v.aweme_id ?? ""}`,
      };
    });

    videos.sort((a: any, b: any) =>
      sort_by === "likes" ? b.likes - a.likes : b.plays - a.plays
    );

    return NextResponse.json({ success: true, count: videos.length, videos });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
