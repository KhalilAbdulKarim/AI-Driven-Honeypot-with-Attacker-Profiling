import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = {
  script_kiddie: '#3b82f6',
  intermediate:  '#10b981',
  advanced:      '#ef4444',
}

export default function SkillChart({ data }) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name: name.replace('_', ' '), value, key: name }))

  return (
    <Card title="Skill distribution">
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie data={chartData} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={70}>
            {chartData.map(d => (
              <Cell key={d.key} fill={COLORS[d.key] || '#6b7280'} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: 'var(--text)' }}
          />
          <Legend iconSize={10} wrapperStyle={{ fontSize: 11, color: 'var(--muted)' }} />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  )
}

function Card({ title, children }) {
  return (
    <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
        {title}
      </div>
      {children}
    </div>
  )
}