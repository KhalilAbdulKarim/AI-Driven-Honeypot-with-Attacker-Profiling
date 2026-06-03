export default function NavBar({ page, setPage, total, lastUpdate, loading }) {
  return (
    <header style={{
      padding: '0 24px',
      borderBottom: '1px solid #2a2d3a',
      background: '#0d0f14',
      position: 'sticky', top: 0, zIndex: 50,
      display: 'flex', alignItems: 'center', gap: 0, height: 48,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 32 }}>
        <span style={{ fontSize: 14, fontWeight: 500, color: '#ef0909' }}>HONEYPOT</span>
      </div>

      {/* nav tabs */}
      <nav style={{ display: 'flex', alignItems: 'stretch', height: '100%', gap: 2 }}>
        {[
          { id: 'dashboard', label: 'Dashboard' },
          { id: 'map',       label: 'Live map'  },
        ].map(({ id, label }) => (
          <button key={id} onClick={() => setPage(id)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            padding: '0 16px', fontSize: 13, height: '100%',
            color: page === id ? '#e2e4ec' : '#6b7280',
            borderBottom: page === id ? '2px solid #3b82f6' : '2px solid transparent',
            transition: 'color .15s, border-color .15s',
          }}>{label}</button>
        ))}
      </nav>

      <span style={{ marginLeft: 'auto', fontSize: 11, color: '#4b5563' }}>
        {loading ? 'Loading…' : lastUpdate ? `Updated ${lastUpdate.toLocaleTimeString()}` : ''}
      </span>
    </header>
  )
}