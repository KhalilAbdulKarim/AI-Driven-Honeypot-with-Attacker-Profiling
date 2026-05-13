import { formatDistanceToNow } from 'date-fns'

const SKILL_STYLE = {
  script_kiddie: { background: '#1e293b', color: '#94a3b8' },
  intermediate:  { background: '#1c2a1e', color: '#4ade80' },
  advanced:      { background: '#2d1515', color: '#f87171' },
}

export default function SessionsTable({ sessions, onSelect }) {
  return (
    <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 14 }}>
        Live sessions — {sessions.length} total
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              {['ID','IP','Country','Cmds','Skill','Intent','Summary','When'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 12px', color: 'var(--muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: .5, borderBottom: '1px solid var(--border)', fontWeight: 500 }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sessions.map(s => (
              <SessionRow key={s.id} session={s} onSelect={onSelect} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SessionRow({ session: s, onSelect }) {
  const [hovered, setHovered] = useState(false)
  return (
    <tr
      onClick={() => onSelect(s.id)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: hovered ? 'var(--bg3)' : 'transparent', cursor: 'pointer', transition: 'background .1s' }}
    >
      <td style={td}><span style={{ fontFamily: 'monospace', color: 'var(--muted)' }}>{s.id}</span></td>
      <td style={td}><span style={{ fontFamily: 'monospace' }}>{s.ip}</span></td>
      <td style={td}>{s.country}</td>
      <td style={td}>{s.total_commands}</td>
      <td style={td}>
        {s.skill_level
          ? <span style={{ ...pill, ...SKILL_STYLE[s.skill_level] }}>{s.skill_level.replace('_',' ')}</span>
          : <span style={{ color: 'var(--muted)' }}>—</span>}
      </td>
      <td style={td}>
        {s.intent
          ? <span style={{ ...pill, background: '#1e1a2e', color: '#a78bfa' }}>{s.intent.replace(/_/g,' ')}</span>
          : <span style={{ color: 'var(--muted)' }}>—</span>}
      </td>
      <td style={{ ...td, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--muted)' }}>
        {s.summary || '—'}
      </td>
      <td style={{ ...td, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
        {s.started_at ? formatDistanceToNow(new Date(s.started_at), { addSuffix: true }) : '—'}
      </td>
    </tr>
  )
}

// useState needed inside SessionRow
import { useState } from 'react'

const td   = { padding: '9px 12px', borderBottom: '1px solid var(--border)', verticalAlign: 'middle' }
const pill = { display: 'inline-block', padding: '2px 8px', borderRadius: 12, fontSize: 11, fontFamily: 'monospace' }