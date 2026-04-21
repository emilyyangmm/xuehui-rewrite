export const runtime = 'edge';
import { NextRequest, NextResponse } from "next/server";

const LIVEPORTRAIT_API = process.env.LIVEPORTRAIT_API_URL || "";

export const maxDuration = 60; // Vercel 最长60秒

export async function POST(req: NextRequest) {
  try {
    if (!LIVEPORTRAIT_API) {
      return NextResponse.json({ success: false, error: "未配置 LIVEPORTRAIT_API_URL" }, { status: 500 });
    }

    const formData = await req.formData();
    const sourceImage = formData.get("source_image") as File;
    const drivingVideo = formData.get("driving_video") as File;

    if (!sourceImage || !drivingVideo) {
      return NextResponse.json({ success: false, error: "请上传照片和视频" }, { status: 400 });
    }

    // 转发到 AutoDL
    const upstream = new FormData();
    upstream.append("source_image", sourceImage);
    upstream.append("driving_video", drivingVideo);

    const res = await fetch(`${LIVEPORTRAIT_API}/generate`, {
      method: "POST",
      body: upstream,
    });

    if (!res.ok) throw new Error(`AutoDL API 错误: ${res.status}`);

    const data = await res.json();
    if (!data.success) throw new Error(data.error || "生成失败");

    // 返回视频地址
    const videoUrl = `${LIVEPORTRAIT_API}/video/${data.task_id}/${data.filename}`;
    return NextResponse.json({ success: true, video_url: videoUrl });

  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
