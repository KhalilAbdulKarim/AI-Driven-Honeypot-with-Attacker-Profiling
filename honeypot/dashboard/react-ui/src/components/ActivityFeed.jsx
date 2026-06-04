import { formatDistanceToNow } from 'date-fns'

const SKILL_COLOR = {
  script_kiddie: '#3b82f6',
  intermediate:  '#f59e0b',
  advanced:      '#ef4444',
}

export default function ActivityFeed({ sessions }) {

  const seen = new Set()
  const unique = [...sessions]
    .sort((a, b) => new Date(b.started_at) - new Date(a.started_at))
    .filter(s => {
      if (seen.has(s.ip)) return false
      seen.add(s.ip)
      return true
    })
    .slice(0, 20)

  return (
    <div style={{ background: '#13161e', border: '1px solid #2a2d3a', borderRadius: 10, padding: 16 }}>
      <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
        Activity feed — {sessions.length} total sessions
      </div>
      <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {unique.length === 0
          ? <div style={{ color: '#4b5563', fontSize: 12 }}>No sessions yet</div>
          : unique.map(s => <FeedItem key={s.id} session={s} />)}
      </div>
    </div>
  )
}

function FeedItem({ session: s }) {
  const color = SKILL_COLOR[s.skill_level] || '#6b7280'
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '8px 1fr auto',
      gap: 10, alignItems: 'start',
      padding: '7px 10px', borderRadius: 6,
      background: '#1a1d27', fontSize: 12,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, marginTop: 3, flexShrink: 0 }} />
      <div>
        <span style={{ fontFamily: 'monospace', color: '#e2e4ec' }}>{s.ip}</span>
        <span style={{ color: '#4b5563', margin: '0 6px' }}>·</span>
        <span style={{ color: '#9ca3af' }}>{s.country}</span>
        {s.skill_level && (
          <>
            <span style={{ color: '#4b5563', margin: '0 6px' }}>·</span>
            <span style={{ color }}>{s.skill_level.replace(/_/g,' ')}</span>
          </>
        )}
        {s.summary && (
          <div style={{ color: '#6b7280', marginTop: 2, lineHeight: 1.4 }}>{s.summary}</div>
        )}
      </div>
      <div style={{ color: '#4b5563', whiteSpace: 'nowrap', fontSize: 11 }}>
        {s.started_at ? formatDistanceToNow(new Date(s.started_at), { addSuffix: true }) : ''}
      </div>
    </div>
  )
}