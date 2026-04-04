import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "https://u946450-b2d1-6dbf3f52.westc.seetacloud.com:8443";

export async function POST(request: NextRequest) {
  try {
    const { video_url } = await request.json();
    
    if (!video_url) {
      return NextResponse.json({ success: false, error: "请提供视频URL" }, { status: 400 });
    }
    
    // 调用后端fetch-video下载并提取文字
    const res = await fetch(`${BACKEND_URL}/fetch-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: video_url }),
    });
    
    if (!res.ok) {
      return NextResponse.json({ success: false, error: `后端调用失败: ${res.status}` }, { status: 500 });
    }
    
    const data = await res.json();
    const taskId = data.task_id;
    
    if (!taskId) {
      return NextResponse.json({ success: false, error: "未获取到任务ID" }, { status: 500 });
    }
    
    // 轮询等待结果（最多等60秒）
    for (let i = 0; i < 12; i++) {
      await new Promise(r => setTimeout(r, 5000));
      const statusRes = await fetch(`${BACKEND_URL}/status/${taskId}`);
      const status = await statusRes.json();
      if (status.status === "done") {
        return NextResponse.json({ success: true, transcript: status.transcript || "" });
      }
      if (status.status === "failed") {
        return NextResponse.json({ success: false, error: status.error || "提取失败" });
      }
    }
    return NextResponse.json({ success: false, error: "超时" });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
