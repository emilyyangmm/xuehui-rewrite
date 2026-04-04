"use client";

import { useState, useRef } from "react";

export default function DigitalHumanPage() {
  const [sourceImage, setSourceImage] = useState<File | null>(null);
  const [sourcePreview, setSourcePreview] = useState<string | null>(null);
  const [drivingVideo, setDrivingVideo] = useState<File | null>(null);
  const [drivingPreview, setDrivingPreview] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [resultVideo, setResultVideo] = useState<string | null>(null);
  const [error, setError] = useState("");
  const imageRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLInputElement>(null);

  const handleImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSourceImage(file);
    setSourcePreview(URL.createObjectURL(file));
    setResultVideo(null);
  };

  const handleVideo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setDrivingVideo(file);
    setDrivingPreview(URL.createObjectURL(file));
    setResultVideo(null);
  };

  const handleGenerate = async () => {
    if (!sourceImage || !drivingVideo) {
      setError("请上传照片和走路视频");
      return;
    }
    setGenerating(true);
    setError("");
    setResultVideo(null);
    setProgress(0);

    // 模拟进度
    const timer = setInterval(() => {
      setProgress(p => Math.min(p + 2, 90));
    }, 1000);

    try {
      const formData = new FormData();
      formData.append("source_image", sourceImage);
      formData.append("driving_video", drivingVideo);

      const res = await fetch("/api/digital-human", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (!data.success) throw new Error(data.error || "生成失败");

      setProgress(100);
      setResultVideo(data.video_url);
    } catch (e: any) {
      setError(e.message || "生成失败，请重试");
    } finally {
      clearInterval(timer);
      setGenerating(false);
    }
  };

  const S = {
    page: { minHeight: "100vh", background: "#0d0d14", color: "#e8e8f0", fontFamily: "'PingFang SC','Hiragino Sans GB',sans-serif", padding: "24px" } as React.CSSProperties,
    header: { borderBottom: "1px solid #1e1e2e", paddingBottom: 20, marginBottom: 32, display: "flex", alignItems: "center", gap: 12 } as React.CSSProperties,
    icon: { width: 38, height: 38, borderRadius: 10, background: "linear-gradient(135deg,#6c63ff,#3ecfcf)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 } as React.CSSProperties,
    grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, maxWidth: 860, margin: "0 auto 24px" } as React.CSSProperties,
    uploadBox: { border: "2px dashed #252540", borderRadius: 14, padding: 24, textAlign: "center" as const, cursor: "pointer", transition: "border-color .2s", background: "#13131f" },
    preview: { width: "100%", borderRadius: 10, maxHeight: 220, objectFit: "cover" as const },
    btn: { width: "100%", maxWidth: 860, margin: "0 auto", display: "block", padding: "14px", borderRadius: 12, background: "linear-gradient(135deg,#6c63ff,#3ecfcf)", border: "none", color: "#fff", fontWeight: 700, fontSize: 16, cursor: "pointer", letterSpacing: "0.05em" } as React.CSSProperties,
    btnDisabled: { opacity: 0.5, cursor: "not-allowed" } as React.CSSProperties,
    progressBar: { height: 6, background: "#1a1a28", borderRadius: 3, overflow: "hidden", marginTop: 16, maxWidth: 860, margin: "16px auto 0" } as React.CSSProperties,
    progressFill: { height: "100%", borderRadius: 3, background: "linear-gradient(90deg,#6c63ff,#3ecfcf)", transition: "width .5s" } as React.CSSProperties,
    error: { maxWidth: 860, margin: "16px auto 0", padding: "12px 16px", background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", borderRadius: 8, color: "#f87171", fontSize: 13 } as React.CSSProperties,
    result: { maxWidth: 860, margin: "24px auto 0", background: "#13131f", borderRadius: 14, border: "1px solid #252540", overflow: "hidden" } as React.CSSProperties,
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div style={S.icon}>🎭</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>数字人生成</div>
          <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>上传照片 + 走路视频 → 自动生成数字人口播视频</div>
        </div>
        <a href="/" style={{ marginLeft: "auto", fontSize: 13, color: "#9988ff", textDecoration: "none" }}>← 返回改写</a>
      </div>

      <div style={S.grid}>
        {/* 上传照片 */}
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: "#ccc" }}>① 上传人像照片</div>
          <div
            style={{ ...S.uploadBox, borderColor: sourceImage ? "#6c63ff" : "#252540" }}
            onClick={() => imageRef.current?.click()}
            onMouseEnter={e => (e.currentTarget.style.borderColor = "#6c63ff")}
            onMouseLeave={e => (e.currentTarget.style.borderColor = sourceImage ? "#6c63ff" : "#252540")}
          >
            {sourcePreview ? (
              <img src={sourcePreview} style={S.preview} alt="人像预览" />
            ) : (
              <div>
                <div style={{ fontSize: 36, marginBottom: 8 }}>🖼️</div>
                <div style={{ fontSize: 14, color: "#888" }}>点击上传正面照片</div>
                <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>建议：清晰正脸，JPG/PNG</div>
              </div>
            )}
            <input ref={imageRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImage} />
          </div>
          {sourceImage && (
            <div style={{ fontSize: 12, color: "#6c63ff", marginTop: 6 }}>✓ {sourceImage.name}</div>
          )}
        </div>

        {/* 上传走路视频 */}
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: "#ccc" }}>② 上传走路视频</div>
          <div
            style={{ ...S.uploadBox, borderColor: drivingVideo ? "#3ecfcf" : "#252540" }}
            onClick={() => videoRef.current?.click()}
            onMouseEnter={e => (e.currentTarget.style.borderColor = "#3ecfcf")}
            onMouseLeave={e => (e.currentTarget.style.borderColor = drivingVideo ? "#3ecfcf" : "#252540")}
          >
            {drivingPreview ? (
              <video src={drivingPreview} style={S.preview} controls muted />
            ) : (
              <div>
                <div style={{ fontSize: 36, marginBottom: 8 }}>🎬</div>
                <div style={{ fontSize: 14, color: "#888" }}>点击上传走路视频</div>
                <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>建议：正面走路，不说话，MP4</div>
              </div>
            )}
            <input ref={videoRef} type="file" accept="video/*" style={{ display: "none" }} onChange={handleVideo} />
          </div>
          {drivingVideo && (
            <div style={{ fontSize: 12, color: "#3ecfcf", marginTop: 6 }}>✓ {drivingVideo.name}</div>
          )}
        </div>
      </div>

      {/* 生成按钮 */}
      <button
        onClick={handleGenerate}
        disabled={generating || !sourceImage || !drivingVideo}
        style={{ ...S.btn, ...(generating || !sourceImage || !drivingVideo ? S.btnDisabled : {}) }}
      >
        {generating ? `⏳ 生成中... ${progress}%` : "🎭 生成数字人视频"}
      </button>

      {/* 进度条 */}
      {generating && (
        <div style={S.progressBar}>
          <div style={{ ...S.progressFill, width: `${progress}%` }} />
        </div>
      )}

      {/* 错误 */}
      {error && <div style={S.error}>⚠ {error}</div>}

      {/* 结果 */}
      {resultVideo && (
        <div style={S.result}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e1e2e", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "#4ade80", fontSize: 18 }}>✅</span>
            <span style={{ fontWeight: 600 }}>数字人视频生成完成！</span>
          </div>
          <div style={{ padding: 20 }}>
            <video src={resultVideo} controls style={{ width: "100%", borderRadius: 10, maxHeight: 480, background: "#000" }} />
            <a
              href={resultVideo}
              download="digital-human.mp4"
              style={{ display: "block", marginTop: 12, padding: "10px", textAlign: "center", borderRadius: 8, border: "1px solid #6c63ff", color: "#9988ff", textDecoration: "none", fontSize: 14 }}
            >
              ⬇ 下载视频
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
