import { NextRequest, NextResponse } from "next/server";

const API = "https://u946450-b29a-1d68bd35.westd.seetacloud.com:8443";
const DOUYIN_COOKIE = process.env.DOUYIN_COOKIE || "";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${API}/user-videos`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Douyin-Cookie": DOUYIN_COOKIE,
      },
      body: JSON.stringify({
        url: body.url,
        sort_by: body.sortBy === "like" ? "likes" : "play",
        count: 20,
      }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || "获取失败");

    // 转换格式兼容前端
    const videos = (data.videos || []).map((v: any) => ({
      id: v.aweme_id,
      title: v.title,
      description: v.title,
      cover: v.cover,
      play_count: v.plays,
      like_count: v.likes,
      comment_count: v.comments,
    }));

    return NextResponse.json({ success: true, author: { nickname: "抖音博主" }, videos });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
