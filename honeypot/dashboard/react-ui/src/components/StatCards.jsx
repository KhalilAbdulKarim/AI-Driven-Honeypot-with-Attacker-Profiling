const cards = [
  { key: s => s.total_sessions,              label: 'Total sessions',    color: 'var(--blue)'   },
  { key: s => s.profiled,                    label: 'Profiled',          color: 'var(--purple)' },
  { key: s => s.skill_counts.advanced || 0,  label: 'Advanced',          color: 'var(--red)'    },
  { key: s => s.skill_counts.intermediate||0,label: 'Intermediate',      color: 'var(--amber)'  },
  { key: s => s.skill_counts.script_kiddie||0,label:'Script kiddies',    color: 'var(--green)'  },
]

export default function StatCards({ stats }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12 }}>
      {cards.map(({ key, label, color }) => (
        <div key={label} style={{
          background: 'var(--bg2)', border: '1px solid var(--border)',
          borderRadius: 10, padding: '14px 16px',
        }}>
          <div style={{ fontSize: 28, fontWeight: 600, color, marginBottom: 4 }}>
            {key(stats)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
            {label}
          </div>
        </div>
      ))}
    </div>
  )
}