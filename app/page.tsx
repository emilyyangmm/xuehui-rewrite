export default function HomePage() {
  return (
    <main style={{ padding: '2rem', textAlign: 'center', position: 'relative' }}>
      <a 
        href="/settings" 
        style={{ 
          position: 'absolute', 
          top: '20px', 
          right: '20px', 
          padding: '0.5rem 1rem', 
          background: '#1f2937', 
          borderRadius: '6px', 
          textDecoration: 'none',
          color: '#9ca3af',
          fontSize: '14px'
        }}
      >
        ⚙️ 设置
      </a>
      <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>薛辉改写工具</h1>
      <p style={{ color: '#888', marginBottom: '2rem' }}>抖音视频拉取、薛辉改写、数字人生成一体化平台</p>
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        <a 
          href="/studio" 
          style={{ 
            padding: '0.75rem 1.5rem', 
            background: '#6366f1', 
            borderRadius: '8px', 
            textDecoration: 'none',
            color: '#fff'
          }}
        >
          进入工作台
        </a>
        <a 
          href="/digital-human" 
          style={{ 
            padding: '0.75rem 1.5rem', 
            background: '#1f2937', 
            borderRadius: '8px', 
            textDecoration: 'none',
            color: '#fff'
          }}
        >
          数字人生成
        </a>
      </div>
    </main>
  );
}
