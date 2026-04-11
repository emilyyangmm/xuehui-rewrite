"use client";
import { useState, useRef } from "react";

const API = "https://u946450-a5fc-9c0da63f.westb.seetacloud.com:8443";

const VOICES = [
  { id: "xiaoxiao", name: "晓晓", desc: "温柔女声" },
  { id: "xiaoyi", name: "晓伊", desc: "活泼女声" },
  { id: "yunjian", name: "云健", desc: "成熟男声" },
  { id: "yunxi", name: "云希", desc: "阳光男声" },
  { id: "yunyang", name: "云扬", desc: "播音男声" },
];

const VIRAL_ELEMENTS = [
  { id: "cost", icon: "💰", title: "成本", coreLogic: "花小钱办大事" },
  { id: "crowd", icon: "👥", title: "人群", coreLogic: "锁定特定群体" },
  { id: "curiosity", icon: "🔍", title: "猎奇", coreLogic: "反常识冷知识" },
  { id: "contrast", icon: "⚡", title: "反差", coreLogic: "制造戏剧冲突" },
  { id: "worst", icon: "👎", title: "最差", coreLogic: "负面情绪引流" },
  { id: "authority", icon: "👑", title: "头牌", coreLogic: "借势权威大牌" },
  { id: "nostalgia", icon: "📼", title: "怀旧", coreLogic: "激活集体记忆" },
  { id: "hormone", icon: "💕", title: "荷尔蒙", coreLogic: "情感社交需求" },
];

const INDUSTRIES = ["职场","教育","美妆","母婴","健身","美食","情感","科技","穿搭","家居","宠物","财经"];

// 获取认证 headers
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof localStorage !== "undefined") {
    const cookie = localStorage.getItem("douyin_cookie");
    const key = localStorage.getItem("qwen_key");
    if (cookie) headers["X-Douyin-Cookie"] = cookie;
    if (key) headers["X-Qwen-Key"] = key;
  }
  return headers;
}

function pollTask(taskId: string, onDone: (d: any) => void, onError: (e: string) => void) {
  const iv = setInterval(async () => {
    try {
      const r = await fetch(`${API}/status/${taskId}`, { headers: getAuthHeaders() });
      const d = await r.json();
      if (d.status === "done") { clearInterval(iv); onDone(d); }
      else if (d.status === "failed") { clearInterval(iv); onError(d.error || "生成失败"); }
    } catch (e) { clearInterval(iv); onError("网络错误"); }
  }, 3000);
}

export default function StudioPage() {
  const [douyinUrl, setDouyinUrl] = useState("");
  const [fetchingScript, setFetchingScript] = useState(false);
  const [sortBy, setSortBy] = useState<"play"|"like">("play");
  const [videos, setVideos] = useState<any[]>([]);
  const [authorInfo, setAuthorInfo] = useState<any>(null);
  const [originalScript, setOriginalScript] = useState("");
  const [rewrittenScript, setRewrittenScript] = useState("");
  const [rewriting, setRewriting] = useState(false);
  const [selectedElements, setSelectedElements] = useState<string[]>([]);
  const [industry, setIndustry] = useState("职场");
  const [titles, setTitles] = useState<string[]>([]);

  const [selectedVoice, setSelectedVoice] = useState("xiaoxiao");
  const [audioUrl, setAudioUrl] = useState("");
  const [generatingAudio, setGeneratingAudio] = useState(false);

  const [sourceImage, setSourceImage] = useState<File | null>(null);
  const [sourcePreview, setSourcePreview] = useState("");
  const [drivingVideo, setDrivingVideo] = useState<File | null>(null);
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [rawVideoUrl, setRawVideoUrl] = useState("");

  const [finalVideo, setFinalVideo] = useState("");
  const [merging, setMerging] = useState(false);
  const [err, setErr] = useState("");
  const [copiedTitle, setCopiedTitle] = useState(-1);

  const imgRef = useRef<HTMLInputElement>(null);
  const vidRef = useRef<HTMLInputElement>(null);

  const toggleEl = (id: string) =>
    setSelectedElements(p => p.includes(id) ? p.filter(x => x !== id) : p.length < 3 ? [...p, id] : p);

  const fetchScript = async () => {
    if (!douyinUrl.trim()) return;
    setFetchingScript(true); setErr(""); setVideos([]); setAuthorInfo(null);
    try {
      const cookie = localStorage.getItem("douyin_cookie") || "";
      const res = await fetch(`${API}/user-videos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: douyinUrl,
          sort_by: sortBy === "like" ? "likes" : "play",
          count: 20,
          cookie: cookie,  // Cookie 放 body 里
        }),
      });
      const d = await res.json();
      if (d.error) throw new Error(d.error);
      setAuthorInfo({ nickname: "博主", avatar: "", followers: 0, total_likes: 0 });
      setVideos((d.videos || []).map((v: any) => ({
        id: v.aweme_id,
        title: v.title,
        description: v.title,
        cover: v.cover,
        play_count: v.plays || 0,
        like_count: v.likes || 0,
        comment_count: v.comments || 0,
        video_url: v.video_url,  // 确保视频URL被保留
      })));
    } catch (e: any) { setErr(e.message); }
    finally { setFetchingScript(false); }
  };

  const selectVideo = async (v: any) => {
    setOriginalScript(v.title || "");
    setRewrittenScript(""); setTitles([]);
    
    console.log("video_url:", v.video_url); // 调试用
    
    if (v.video_url) {
      setErr("正在提取视频文案，约1-2分钟…");
      try {
        const cookie = localStorage.getItem("douyin_cookie") || "";
        const payload = { video_url: v.video_url, cookie };
        console.log("发送payload:", JSON.stringify(payload).slice(0, 100));
        
        const res = await fetch("/api/asr", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const d = await res.json();
        console.log("asr响应:", d);
        if (d.task_id) {
          pollTask(d.task_id,
            (sd) => { setOriginalScript(sd.transcript || v.title || ""); setErr(""); },
            () => { setOriginalScript(v.title || ""); setErr(""); }
          );
        }
      } catch (e) {
        setErr("");
      }
    }
  };

  const rewrite = async () => {
    if (!originalScript.trim()) return;
    setRewriting(true); setErr("");
    try {
      const qwenKey = localStorage.getItem("qwen_key") || "";
      const res = await fetch(`${API}/rewrite`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Qwen-Key": qwenKey,
        },
        body: JSON.stringify({ text: originalScript }),
      });
      const d = await res.json();
      setRewrittenScript(d.result || "");
      setTitles([]);
    } catch (e: any) { setErr(e.message); }
    finally { setRewriting(false); }
  };

  const generateAudio = async () => {
    if (!rewrittenScript.trim()) { setErr("请先改写文案"); return; }
    setGeneratingAudio(true); setAudioUrl(""); setErr("");
    try {
      const fd = new FormData();
      fd.append("text", rewrittenScript);
      fd.append("voice", selectedVoice);
      const r = await fetch(`${API}/generate-audio`, { method: "POST", body: fd });
      const d = await r.json();
      if (!d.success) throw new Error(d.error);
      pollTask(d.task_id,
        (data) => { setAudioUrl(data.audio_url); setGeneratingAudio(false); },
        (e) => { setErr(e); setGeneratingAudio(false); }
      );
    } catch (e: any) { setErr(e.message); setGeneratingAudio(false); }
  };

  const genVideo = async () => {
    if (!drivingVideo) { setErr("请上传你的视频"); return; }
    if (!audioUrl) { setErr("请先生成口播音频"); return; }
    setGeneratingVideo(true); setRawVideoUrl(""); setErr("");
    try {
      // 先下载TTS音频
      const audioBlob = await fetch(audioUrl).then(r => r.blob());
      const fd = new FormData();
      fd.append("source_video", drivingVideo);
      fd.append("audio_file", audioBlob, "audio.mp3");
      const r = await fetch(`${API}/generate-video`, { method: "POST", body: fd });
      const d = await r.json();
      if (!d.success) throw new Error(d.error);
      pollTask(d.task_id,
        (data) => { setRawVideoUrl(data.video_url); setGeneratingVideo(false); },
        (e) => { setErr(e); setGeneratingVideo(false); }
      );
    } catch (e: any) { setErr(e.message); setGeneratingVideo(false); }
  };

  const merge = async () => {
    if (!rawVideoUrl || !audioUrl) { setErr("请先生成视频和音频"); return; }
    setMerging(true); setFinalVideo(""); setErr("");
    try {
      const fd = new FormData();
      fd.append("video_url", rawVideoUrl);
      fd.append("audio_url", audioUrl);
      fd.append("subtitle_text", rewrittenScript || originalScript);
      const r = await fetch(`${API}/merge`, { method: "POST", headers: getAuthHeaders(), body: fd });
      const d = await r.json();
      if (!d.success) throw new Error(d.error);
      pollTask(d.task_id,
        (data) => { setFinalVideo(data.video_url); setMerging(false); },
        (e) => { setErr(e); setMerging(false); }
      );
    } catch (e: any) { setErr(e.message); setMerging(false); }
  };

  const copyTitle = (t: string, i: number) => {
    navigator.clipboard.writeText(t);
    setCopiedTitle(i);
    setTimeout(() => setCopiedTitle(-1), 2000);
  };

  const fmt = (n: number) => n >= 10000 ? (n / 10000).toFixed(1) + "w" : String(n);

  const done = { script: !!rewrittenScript, audio: !!audioUrl, video: !!rawVideoUrl, final: !!finalVideo };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#060812", color: "#e2e8f0", fontFamily: "'PingFang SC','Hiragino Sans GB',sans-serif", overflow: "hidden" }}>

      {/* Header — fixed height, no overlap */}
      <div style={{ height: 48, minHeight: 48, borderBottom: "1px solid #0f172a", background: "#080d1a", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, zIndex: 10, flexShrink: 0 }}>
        <div style={{ width: 26, height: 26, borderRadius: 7, background: "linear-gradient(135deg,#818cf8,#22d3ee)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>⚡</div>
        <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: "0.1em", background: "linear-gradient(90deg,#818cf8,#22d3ee)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>DIGITAL STUDIO</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          {err && <span style={{ fontSize: 11, color: "#f87171", background: "rgba(248,113,113,.1)", padding: "3px 10px", borderRadius: 6, border: "1px solid rgba(248,113,113,.2)", maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>⚠ {err}</span>}
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22d3ee", boxShadow: "0 0 6px #22d3ee" }} />
          <span style={{ fontSize: 10, color: "#334155", letterSpacing: "0.1em" }}>LIVE</span>
        </div>
      </div>

      {/* 3 columns — fill remaining height */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", minHeight: 0, overflow: "hidden" }}>

        {/* ══ COL 1: 文案 ══ */}
        <div style={{ borderRight: "1px solid #0f172a", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <ColHeader label="01" title="文案生产" color="#818cf8" />
          <div style={{ flex: 1, overflowY: "auto", padding: "0 0 20px" }}>

            <Section title="抖音链接" icon="🔗">
              <div style={{ display: "flex", gap: 5, marginBottom: 6 }}>
                <input value={douyinUrl} onChange={e => setDouyinUrl(e.target.value)} placeholder="博主主页或单个视频链接…" style={inputStyle} onKeyDown={e => e.key === "Enter" && fetchScript()} />
                <Btn onClick={fetchScript} loading={fetchingScript} color="#818cf8">拉取</Btn>
              </div>
              {/* 排序 */}
              <div style={{ display: "flex", gap: 4 }}>
                {["play", "like"].map(s => (
                  <button key={s} onClick={() => setSortBy(s as any)} style={{ padding: "3px 10px", borderRadius: 10, fontSize: 11, border: "1px solid", borderColor: sortBy === s ? "#818cf8" : "#1e293b", background: sortBy === s ? "rgba(129,140,248,.15)" : "transparent", color: sortBy === s ? "#818cf8" : "#475569", cursor: "pointer" }}>
                    {s === "play" ? "▶ 播放量" : "♥ 点赞量"}
                  </button>
                ))}
              </div>
            </Section>

            {/* 视频列表 */}
            {authorInfo && (
              <Section title={`${authorInfo.nickname} · ${videos.length}条视频`} icon="👤">
                <div style={{ display: "flex", flexDirection: "column", gap: 5, maxHeight: 200, overflowY: "auto" }}>
                  {videos.map((v, i) => (
                    <div key={v.id} onClick={() => selectVideo(v)} style={{ display: "flex", gap: 8, padding: "7px 8px", background: "#0a0f1e", borderRadius: 7, border: "1px solid #0f172a", cursor: "pointer" }}
                      onMouseEnter={e => (e.currentTarget.style.borderColor = "#818cf8")}
                      onMouseLeave={e => (e.currentTarget.style.borderColor = "#0f172a")}>
                      <div style={{ width: 36, height: 48, borderRadius: 5, background: "#1e293b", overflow: "hidden", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#475569" }}>
                        {v.cover ? <img src={v.cover} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : `#${i+1}`}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 11, color: "#cbd5e1", lineHeight: 1.4, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>{v.title}</div>
                        <div style={{ fontSize: 10, color: "#334155", marginTop: 3 }}>▶ {fmt(v.play_count)} · ♥ {fmt(v.like_count)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            <Section title="原始文案" icon="📄">
              <textarea value={originalScript} onChange={e => setOriginalScript(e.target.value)} placeholder="点击上方视频选取，或手动粘贴文案…" rows={4} style={taStyle} />
            </Section>

            <Section title="爆款元素（最多3个）" icon="🔥">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 7 }}>
                {VIRAL_ELEMENTS.map(el => (
                  <button key={el.id} onClick={() => toggleEl(el.id)} style={{ padding: "3px 9px", borderRadius: 10, fontSize: 11, border: "1px solid", borderColor: selectedElements.includes(el.id) ? "#818cf8" : "#1e293b", background: selectedElements.includes(el.id) ? "rgba(129,140,248,.15)" : "transparent", color: selectedElements.includes(el.id) ? "#818cf8" : "#475569", cursor: selectedElements.length >= 3 && !selectedElements.includes(el.id) ? "not-allowed" : "pointer", opacity: selectedElements.length >= 3 && !selectedElements.includes(el.id) ? 0.4 : 1 }}>
                    {el.icon} {el.title}
                  </button>
                ))}
              </div>
              <div style={{ marginTop: 8 }}>
                <Btn onClick={rewrite} loading={rewriting} color="#818cf8">⚡ 薛辉改写</Btn>
              </div>
            </Section>

            <Section title="改写文案" icon="✨">
              <textarea value={rewrittenScript} onChange={e => setRewrittenScript(e.target.value)} placeholder="改写后在此显示，可直接编辑…" rows={6} style={taStyle} />
              {rewrittenScript && (
                <button onClick={() => navigator.clipboard.writeText(rewrittenScript)} style={{ marginTop: 5, padding: "3px 12px", borderRadius: 6, background: "none", border: "1px solid #1e293b", color: "#475569", fontSize: 11, cursor: "pointer" }}>复制文案</button>
              )}
            </Section>

            <Section title="爆款标题" icon="🏷">
              {titles.length === 0 ? (
                <div style={{ fontSize: 11, color: "#334155" }}>改写后自动生成标题…</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {titles.map((t, i) => (
                    <div key={i} style={{ display: "flex", gap: 6, padding: "6px 8px", background: "#0a0f1e", borderRadius: 6, border: "1px solid #0f172a", alignItems: "flex-start" }}>
                      <span style={{ fontSize: 11, color: "#94a3b8", flex: 1, lineHeight: 1.5 }}>{t}</span>
                      <button onClick={() => copyTitle(t, i)} style={{ background: "none", border: "none", color: copiedTitle === i ? "#22d3ee" : "#334155", fontSize: 10, cursor: "pointer", flexShrink: 0 }}>
                        {copiedTitle === i ? "✓" : "复制"}
                      </button>
                    </div>
                  ))}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginTop: 4 }}>
                    {["#" + industry, "#干货分享", "#涨知识", "#每日学习", "#实用技巧"].map(t => (
                      <span key={t} style={{ fontSize: 10, padding: "2px 7px", borderRadius: 8, background: "rgba(34,211,238,.08)", border: "1px solid rgba(34,211,238,.15)", color: "#22d3ee" }}>{t}</span>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          </div>
        </div>

        {/* ══ COL 2: 生产 ══ */}
        <div style={{ borderRight: "1px solid #0f172a", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <ColHeader label="02" title="视频生产" color="#22d3ee" />
          <div style={{ flex: 1, overflowY: "auto", padding: "0 0 20px" }}>

            <Section title="声音选择" icon="🎙">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 5 }}>
                {VOICES.map(v => (
                  <button key={v.id} onClick={() => setSelectedVoice(v.id)} style={{ padding: "7px 8px", borderRadius: 7, border: "1px solid", borderColor: selectedVoice === v.id ? "#22d3ee" : "#1e293b", background: selectedVoice === v.id ? "rgba(34,211,238,.08)" : "#0a0f1e", cursor: "pointer", textAlign: "left" as const }}>
                    <div style={{ fontWeight: 600, fontSize: 12, color: selectedVoice === v.id ? "#22d3ee" : "#cbd5e1" }}>{v.name}</div>
                    <div style={{ fontSize: 10, color: "#475569" }}>{v.desc}</div>
                  </button>
                ))}
              </div>
              <div style={{ marginTop: 7 }}>
                <Btn onClick={generateAudio} loading={generatingAudio} color="#22d3ee" full>🎙 生成口播音频</Btn>
              </div>
              {generatingAudio && <div style={{ fontSize: 11, color: "#475569", marginTop: 5 }}>⏳ 生成中，约10-20秒…</div>}
              {audioUrl && (
                <div style={{ marginTop: 7 }}>
                  <audio src={audioUrl} controls style={{ width: "100%", height: 28 }} />
                  <div style={{ fontSize: 10, color: "#22d3ee", marginTop: 3 }}>✓ 音频生成完成</div>
                </div>
              )}
            </Section>

            {/* 上传驱动视频 */}
            <Section title="上传你的视频（不说话）" icon="🎬">
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>录一段你不说话的视频（走路/站立/点头），系统会把你的动作套在照片上</div>
              <div onClick={() => vidRef.current?.click()} style={{ border: "1px dashed #1e293b", borderRadius: 10, height: 80, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", background: "#0a0f1e" }}>
                {drivingVideo ? (
                  <div style={{ textAlign: "center" as const, color: "#22d3ee" }}>
                    <div style={{ fontSize: 16 }}>✓</div>
                    <div style={{ fontSize: 11 }}>{drivingVideo.name}</div>
                  </div>
                ) : (
                  <div style={{ textAlign: "center" as const, color: "#334155" }}>
                    <div style={{ fontSize: 28 }}>🎥</div>
                    <div style={{ fontSize: 11, marginTop: 4 }}>点击上传视频（MP4）</div>
                  </div>
                )}
                <input ref={vidRef} type="file" accept="video/*" style={{ display: "none" }} onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) setDrivingVideo(f);
                }} />
              </div>
              <div style={{ marginTop: 7 }}>
                <Btn onClick={genVideo} loading={generatingVideo} color="#22d3ee" full>🎭 生成数字人视频</Btn>
              </div>
              {generatingVideo && <div style={{ fontSize: 11, color: "#475569", marginTop: 5 }}>⏳ 生成中，约1-2分钟…</div>}
              {rawVideoUrl && <div style={{ fontSize: 10, color: "#22d3ee", marginTop: 5 }}>✓ 数字人视频生成完成</div>}
            </Section>

            <Section title="合并输出" icon="🎬">
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 7 }}>将数字人视频 + 口播音频 + 字幕合并为最终视频</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                <StatusRow label="口播音频" done={done.audio} />
                <StatusRow label="数字人视频" done={done.video} />
              </div>
              <Btn onClick={merge} loading={merging} color="#a78bfa" full>
                {merging ? "合并中，请稍候…" : "⚡ 一键合并"}
              </Btn>
              {merging && <div style={{ fontSize: 11, color: "#475569", marginTop: 5 }}>⏳ 合并中，约30-60秒…</div>}
            </Section>
          </div>
        </div>

        {/* ══ COL 3: 预览发布 ══ */}
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <ColHeader label="03" title="预览发布" color="#a78bfa" />
          <div style={{ flex: 1, overflowY: "auto", padding: "0 0 20px" }}>

            <Section title="视频预览" icon="▶">
              <div style={{ background: "#0a0f1e", borderRadius: 10, border: "1px solid #0f172a", overflow: "hidden", aspectRatio: "9/16", maxHeight: 360, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {finalVideo ? (
                  <video src={finalVideo} controls style={{ width: "100%", height: "100%", objectFit: "contain" as const }} />
                ) : rawVideoUrl ? (
                  <video src={rawVideoUrl} controls style={{ width: "100%", height: "100%", objectFit: "contain" as const }} />
                ) : (
                  <div style={{ textAlign: "center" as const, color: "#1e293b" }}>
                    <div style={{ fontSize: 40 }}>▶</div>
                    <div style={{ fontSize: 11, marginTop: 6 }}>生成后在此预览</div>
                  </div>
                )}
              </div>
              {(finalVideo || rawVideoUrl) && (
                <button onClick={() => {
                  const url = finalVideo || rawVideoUrl;
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'digital_human.mp4';
                  a.target = '_blank';
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                }} style={{ display: "block", width: "100%", marginTop: 7, padding: "8px", textAlign: "center" as const, borderRadius: 7, border: "1px solid #a78bfa", color: "#a78bfa", textDecoration: "none", fontSize: 12, background: "rgba(167,139,250,.08)", cursor: "pointer" }}>
                  ⬇ 下载视频
                </button>
              )}
            </Section>

            <Section title="一键发布" icon="🚀">
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <button onClick={() => {
                  const text = `${titles[0] || ""}\n\n${rewrittenScript || originalScript}\n\n#${industry} #干货分享 #涨知识`;
                  navigator.clipboard.writeText(text);
                  window.open("https://creator.douyin.com/creator-micro/content/upload", "_blank");
                }} style={{ padding: "10px", borderRadius: 7, background: "linear-gradient(135deg,#a78bfa,#818cf8)", border: "none", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
                  📱 复制文案 → 发布抖音
                </button>
                <button onClick={() => window.open("https://channels.weixin.qq.com/platform/post/create", "_blank")}
                  style={{ padding: "9px", borderRadius: 7, background: "#0a0f1e", border: "1px solid #1e293b", color: "#64748b", fontSize: 12, cursor: "pointer" }}>
                  🟢 发布视频号
                </button>
                <button onClick={() => window.open("https://www.xiaohongshu.com/publish/publish", "_blank")}
                  style={{ padding: "9px", borderRadius: 7, background: "#0a0f1e", border: "1px solid #1e293b", color: "#64748b", fontSize: 12, cursor: "pointer" }}>
                  📕 发布小红书
                </button>
              </div>
            </Section>

            <Section title="生产进度" icon="📊">
              <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                <StatusRow label="文案改写" done={done.script} />
                <StatusRow label="音频生成" done={done.audio} />
                <StatusRow label="数字人视频" done={done.video} />
                <StatusRow label="最终合成" done={done.final} />
              </div>
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}

function ColHeader({ label, title, color }: { label: string; title: string; color: string }) {
  return (
    <div style={{ height: 40, minHeight: 40, padding: "0 14px", borderBottom: "1px solid #0f172a", display: "flex", alignItems: "center", gap: 8, background: "#080d1a", flexShrink: 0 }}>
      <span style={{ fontSize: 10, fontWeight: 800, color, letterSpacing: "0.15em", opacity: 0.5 }}>{label}</span>
      <div style={{ width: 1, height: 12, background: "#1e293b" }} />
      <span style={{ fontWeight: 700, fontSize: 12, letterSpacing: "0.1em", color }}>{title}</span>
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: "10px 12px", borderBottom: "1px solid #080d1a" }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: "#334155", letterSpacing: "0.08em", marginBottom: 7, display: "flex", alignItems: "center", gap: 4 }}>
        <span>{icon}</span> {title.toUpperCase()}
      </div>
      {children}
    </div>
  );
}

function StatusRow({ label, done }: { label: string; done: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 8px", background: "#0a0f1e", borderRadius: 5 }}>
      <div style={{ width: 7, height: 7, borderRadius: "50%", background: done ? "#22d3ee" : "#1e293b", boxShadow: done ? "0 0 5px #22d3ee" : "none", flexShrink: 0 }} />
      <span style={{ fontSize: 11, color: done ? "#94a3b8" : "#334155" }}>{label}</span>
      {done && <span style={{ marginLeft: "auto", fontSize: 10, color: "#22d3ee" }}>✓</span>}
    </div>
  );
}

function Btn({ onClick, loading, color, full, children }: any) {
  return (
    <button onClick={onClick} disabled={loading} style={{ padding: "7px 12px", borderRadius: 6, background: loading ? "#0f172a" : `${color}18`, border: `1px solid ${loading ? "#1e293b" : color + "44"}`, color: loading ? "#334155" : color, fontSize: 11, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", width: full ? "100%" : "auto", transition: "all .15s" }}>
      {loading ? "处理中…" : children}
    </button>
  );
}

const inputStyle: React.CSSProperties = { flex: 1, padding: "6px 9px", borderRadius: 6, background: "#0a0f1e", border: "1px solid #1e293b", color: "#e2e8f0", fontSize: 11, outline: "none" };
const taStyle: React.CSSProperties = { width: "100%", padding: "7px 9px", borderRadius: 6, background: "#0a0f1e", border: "1px solid #1e293b", color: "#e2e8f0", fontSize: 11, resize: "vertical" as const, outline: "none", lineHeight: 1.7, boxSizing: "border-box" as const };
