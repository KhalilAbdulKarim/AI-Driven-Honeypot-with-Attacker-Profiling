import { useState, useEffect, useCallback } from 'react'
import { fetchSessions, fetchStats } from './api'
import StatCards     from './components/StatCards'
import SkillChart    from './components/SkillChart'
import IntentChart   from './components/IntentChart'
import TopLists      from './components/TopLists'
import SessionsTable from './components/SessionsTable'
import SessionModal  from './components/SessionModal'
import ActivityFeed  from './components/ActivityFeed'
import CostTracker   from './components/CostTracker'
import NavBar        from './components/NavBar'
import LiveMapPage   from './components/LiveMapPage'

const REFRESH_MS = 10000

export default function App() {
  const [sessions,   setSessions]   = useState([])
  const [stats,      setStats]      = useState(null)
  const [selected,   setSelected]   = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [page,       setPage]       = useState('dashboard')

  const refresh = useCallback(async () => {
    try {
      const [s, st] = await Promise.all([fetchSessions(), fetchStats()])
      setSessions(s)
      setStats(st)
      setLastUpdate(new Date())
    } catch (e) {
      console.error('Refresh failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, REFRESH_MS)
    return () => clearInterval(id)
  }, [refresh])

  return (
    <div style={{ minHeight: '100vh', background: '#0d0f14' }}>
      <NavBar
        page={page} setPage={setPage}
        total={sessions.length}
        lastUpdate={lastUpdate}
        loading={loading}
      />

      {page === 'map' ? (
        <LiveMapPage sessions={sessions} />
      ) : (
        <main style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>

          {stats && <StatCards stats={stats} />}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {stats && <SkillChart  data={stats.skill_counts} />}
            {stats && <IntentChart data={stats.intent_counts} />}
            {stats && <TopLists   stats={stats} />}
          </div>

          <ActivityFeed sessions={sessions} />

          {stats && <CostTracker stats={stats} />}

          <SessionsTable sessions={sessions} onSelect={setSelected} />

        </main>
      )}

      {selected && page !== 'map' && (
        <SessionModal sessionId={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}