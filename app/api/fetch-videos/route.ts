export const runtime = 'edge';
import { NextRequest, NextResponse } from "next/server";
const API = process.env.BACKEND_URL || "https://u946450-a783-20029e21.westc.seetacloud.com:8443";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const cookie = req.headers.get("X-Douyin-Cookie") || process.env.DOUYIN_COOKIE || "";
    const res = await fetch(`${API}/user-videos`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Douyin-Cookie": cookie },
      body: JSON.stringify({ url: body.url, sort_by: body.sortBy === "like" ? "likes" : "play", count: 20 }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || "获取失败");
    const videos = (data.videos || []).map((v: any) => ({
      id: v.aweme_id, title: v.title, description: v.title,
      cover: v.cover, play_count: v.plays, like_count: v.likes, comment_count: v.comments,
      video_url: v.video_url,  // 确保视频URL被保留
    }));
    return NextResponse.json({ success: true, author: { nickname: "抖音博主" }, videos });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
