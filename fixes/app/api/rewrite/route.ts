import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "https://u946450-b2d1-6dbf3f52.westc.seetacloud.com:8443";

// 清除舞台提示词：括号内的导演提示、语气说明等
function removeStageDirections(text: string): string {
  return text
    .replace(/[（(][^）)]{1,30}[）)]/g, "") // 删除括号内短提示
    .replace(/【[^】]{1,20}】/g, "")         // 删除【】内提示
    .replace(/\[.*?\]/g, "")                 // 删除[]内提示
    .replace(/^(开场|转折|结尾|高潮|铺垫)[：:]\s*/gm, "") // 删除段落标题
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

async function rewriteText(text: string): Promise<string> {
  const res = await fetch(`${BACKEND_URL}/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`后端调用失败: ${res.status}`);
  const data = await res.json();
  return data.rewritten_text || data.script || "";
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action, text, industry, scriptType, selectedElements, selectedHooks, author_videos } = body;
    
    if (action === "rewrite") {
      // 改写文案
      if (!text?.trim()) {
        return NextResponse.json({ success: false, error: "请输入文案" }, { status: 400 });
      }
      const rewrittenText = await rewriteText(text);
      return NextResponse.json({ success: true, rewritten_text: rewrittenText });
    }
    
    if (action === "generate_titles") {
      // 生成选题标题
      const res = await fetch(`${BACKEND_URL}/generate-titles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, industry, count: 8 }),
      });
      const data = await res.json();
      return NextResponse.json(data);
    }
    
    if (action === "analyze_industry") {
      // 分析账号定位
      if (!author_videos?.length) {
        return NextResponse.json({ success: false, error: "请提供账号视频数据" }, { status: 400 });
      }
      const res = await fetch(`${BACKEND_URL}/analyze-industry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ videos: author_videos }),
      });
      const data = await res.json();
      return NextResponse.json(data);
    }
    
    if (action === "generate_mix") {
      // 生成混剪脚本
      const res = await fetch(`${BACKEND_URL}/generate-mix-script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, industry, scriptType, selectedElements, selectedHooks }),
      });
      const data = await res.json();
      return NextResponse.json(data);
    }
    
    // 没有action时默认当rewrite处理（向后兼容）
    if (text?.trim()) {
      const rewrittenText = await rewriteText(text);
      return NextResponse.json({ success: true, rewritten_text: rewrittenText });
    }
    
    return NextResponse.json({ success: false, error: "未知的 action" }, { status: 400 });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}
