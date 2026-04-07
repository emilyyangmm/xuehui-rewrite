"use client";
import { useState, useEffect } from "react";

export default function SettingsPage() {
  const [douyinCookie, setDouyinCookie] = useState("");
  const [qwenKey, setQwenKey] = useState("");
  const [activationCode, setActivationCode] = useState("");
  const [machineCode, setMachineCode] = useState("");
  const [saved, setSaved] = useState(false);
  const [activationStatus, setActivationStatus] = useState<"unknown"|"valid"|"invalid">("unknown");

  useEffect(() => {
    setDouyinCookie(localStorage.getItem("douyin_cookie") || "");
    setQwenKey(localStorage.getItem("qwen_key") || "");
    setActivationCode(localStorage.getItem("activation_code") || "");
    // 获取机器码
    fetch("/api/machine-code").then(r => r.json()).then(d => {
      if (d.machine_code) setMachineCode(d.machine_code);
    }).catch(() => {});
  }, []);

  const handleSave = () => {
    localStorage.setItem("douyin_cookie", douyinCookie);
    localStorage.setItem("qwen_key", qwenKey);
    localStorage.setItem("activation_code", activationCode);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleVerify = async () => {
    const res = await fetch("/api/verify-license", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activation_code: activationCode }),
    });
    const data = await res.json();
    setActivationStatus(data.valid ? "valid" : "invalid");
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "white", padding: "40px 20px" }}>
      <div style={{ maxWidth: 600, margin: "0 auto" }}>
        <h1 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 8 }}>⚙️ 账号设置</h1>
        <p style={{ color: "#64748b", marginBottom: 32 }}>配置你的账号信息，数据仅保存在本地浏览器</p>

        {/* 机器码 */}
        <div style={{ background: "#0f172a", borderRadius: 12, padding: 20, marginBottom: 16, border: "1px solid #1e293b" }}>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>🖥️ 机器码（发给管理员获取激活码）</div>
          <div style={{ display: "flex", gap: 8 }}>
            <input readOnly value={machineCode || "获取中..."} style={{ flex: 1, background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", color: "#94a3b8", fontSize: 12 }} />
            <button onClick={() => navigator.clipboard.writeText(machineCode)} style={{ background: "#334155", border: "none", borderRadius: 8, padding: "8px 16px", color: "white", cursor: "pointer", fontSize: 13 }}>复制</button>
          </div>
        </div>

        {/* 激活码 */}
        <div style={{ background: "#0f172a", borderRadius: 12, padding: 20, marginBottom: 16, border: "1px solid #1e293b" }}>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>🔑 激活码</div>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={activationCode} onChange={e => setActivationCode(e.target.value)} placeholder="输入激活码..." style={{ flex: 1, background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", color: "white", fontSize: 13 }} />
            <button onClick={handleVerify} style={{ background: "#6366f1", border: "none", borderRadius: 8, padding: "8px 16px", color: "white", cursor: "pointer", fontSize: 13 }}>验证</button>
          </div>
          {activationStatus === "valid" && <div style={{ color: "#22c55e", fontSize: 12, marginTop: 6 }}>✅ 激活成功</div>}
          {activationStatus === "invalid" && <div style={{ color: "#ef4444", fontSize: 12, marginTop: 6 }}>❌ 激活码无效</div>}
        </div>

        {/* 抖音Cookie */}
        <div style={{ background: "#0f172a", borderRadius: 12, padding: 20, marginBottom: 16, border: "1px solid #1e293b" }}>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 4 }}>🎵 抖音 Cookie</div>
          <div style={{ fontSize: 11, color: "#475569", marginBottom: 8 }}>
            打开 douyin.com → F12 → Network → 任意请求 → Request Headers → 复制 Cookie 字段
          </div>
          <textarea value={douyinCookie} onChange={e => setDouyinCookie(e.target.value)} placeholder="粘贴抖音Cookie..." rows={4} style={{ width: "100%", background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", color: "white", fontSize: 11, resize: "vertical", boxSizing: "border-box" }} />
        </div>

        {/* Qwen API Key */}
        <div style={{ background: "#0f172a", borderRadius: 12, padding: 20, marginBottom: 24, border: "1px solid #1e293b" }}>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 4 }}>🤖 阿里云 Qwen API Key（可选）</div>
          <div style={{ fontSize: 11, color: "#475569", marginBottom: 8 }}>不填则使用系统默认，填写后使用你自己的额度</div>
          <input value={qwenKey} onChange={e => setQwenKey(e.target.value)} placeholder="sk-..." style={{ width: "100%", background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", color: "white", fontSize: 13, boxSizing: "border-box" }} />
        </div>

        <button onClick={handleSave} style={{ width: "100%", background: "#6366f1", border: "none", borderRadius: 10, padding: "12px", color: "white", fontSize: 16, fontWeight: "bold", cursor: "pointer" }}>
          {saved ? "✅ 已保存" : "💾 保存设置"}
        </button>
      </div>
    </div>
  );
}
