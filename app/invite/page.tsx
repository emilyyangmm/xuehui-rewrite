'use client';
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function InvitePage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("invite_verified") === "true") {
      router.replace("/studio");
    }
  }, [router]);

  const handleVerify = async () => {
    if (!code.trim()) { setErr("请输入邀请码"); return; }
    setLoading(true);
    setErr("");
    try {
      const res = await fetch("/api/verify-invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.trim() }),
      });
      const d = await res.json();
      if (d.success) {
        localStorage.setItem("invite_verified", "true");
        router.replace("/studio");
      } else {
        setErr(d.error || "邀请码无效");
      }
    } catch {
      setErr("验证失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#060812", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'PingFang SC','Hiragino Sans GB',sans-serif" }}>
      <div style={{ textAlign: "center", padding: "40px 24px", maxWidth: 400, width: "100%" }}>
        <div style={{ width: 56, height: 56, borderRadius: 16, background: "linear-gradient(135deg,#818cf8,#22d3ee)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, margin: "0 auto 20px" }}>⚡</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, background: "linear-gradient(90deg,#818cf8,#22d3ee)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>DIGITAL STUDIO</h1>
        <p style={{ color: "#64748b", fontSize: 13, marginBottom: 32 }}>薛辉内容创作工作室</p>
        
        <div style={{ background: "#0f172a", borderRadius: 16, padding: 28, border: "1px solid #1e293b" }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>请输入邀请码</div>
          <div style={{ fontSize: 12, color: "#475569", marginBottom: 20 }}>联系管理员获取邀请码</div>
          
          <input
            value={code}
            onChange={e => setCode(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleVerify()}
            placeholder="输入邀请码..."
            style={{ width: "100%", padding: "12px 16px", borderRadius: 10, background: "#1e293b", border: "1px solid #334155", color: "white", fontSize: 14, outline: "none", boxSizing: "border-box", marginBottom: 12, textAlign: "center" }}
          />
          
          {err && <div style={{ fontSize: 12, color: "#f87171", marginBottom: 12 }}>⚠ {err}</div>}
          
          <button
            onClick={handleVerify}
            disabled={loading}
            style={{ width: "100%", padding: "12px", borderRadius: 10, background: loading ? "#334155" : "#6366f1", border: "none", color: "white", fontSize: 15, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "验证中…" : "进入工作台"}
          </button>
        </div>
      </div>
    </div>
  );
}
