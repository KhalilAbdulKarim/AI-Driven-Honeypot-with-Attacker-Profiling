export default function TopLists({ stats }) {
  return (
    <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Section title="Top credentials" items={stats.top_credentials}
        label={i => `${i.username}:${i.password}`} mono />
      <Section title="Top commands" items={stats.top_commands}
        label={i => i.command} mono color="var(--cyan)" />
    </div>
  )
}

function Section({ title, items, label, mono, color = 'var(--text)' }) {
  const max = items[0]?.count || 1
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
        {title}
      </div>
      {items.slice(0, 6).map((item, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
            <span style={{ fontFamily: mono ? 'monospace' : 'inherit', fontSize: 12, color }}>{label(item)}</span>
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>{item.count}</span>
          </div>
          <div style={{ height: 4, background: 'var(--bg3)', borderRadius: 2 }}>
            <div style={{ height: 4, borderRadius: 2, background: 'var(--blue)', width: `${Math.round(item.count / max * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}