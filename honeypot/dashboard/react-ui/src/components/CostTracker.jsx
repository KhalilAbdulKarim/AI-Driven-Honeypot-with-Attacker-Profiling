export default function CostTracker({ stats }) {
  const tu = stats?.token_usage || {}
  const cost = tu.estimated_usd || 0
  const perSession = stats?.profiled > 0
    ? (cost / stats.profiled).toFixed(5)
    : '0.00000'

  return (
    <div style={{
      background: '#13161e', border: '1px solid #2a2d3a',
      borderRadius: 10, padding: 16,
      display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12,
    }}>
      {[
        { label: 'Est. total cost', value: `$${cost.toFixed(4)}`,    color: '#10b981' },
        { label: 'Tokens used',     value: (tu.input||0) + (tu.output||0), color: '#8b5cf6' },
        { label: 'Cost / session',  value: `$${perSession}`,          color: '#f59e0b' },
      ].map(({ label, value, color }) => (
        <div key={label}>
          <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
            {label}
          </div>
          <div style={{ fontSize: 20, fontWeight: 600, color }}>{value}</div>
        </div>
      ))}
    </div>
  )
}