import { useEffect, useRef, useState } from 'react'

const SKILL_COLOR = {
  advanced:      '#ef4444',
  intermediate:  '#f59e0b',
  script_kiddie: '#3b82f6',
}

export default function LiveMapPage({ sessions }) {
  const mapRef  = useRef(null)
  const leafRef = useRef(null)
  const layerRef = useRef(null)
  const [selected, setSelected] = useState(null)
  const [filter, setFilter]     = useState('all')

  useEffect(() => {
    if (leafRef.current) return
    const L = window.L
    if (!L) return

    const map = L.map(mapRef.current, {
      center: [30, 30], zoom: 3, minZoom: 2, maxZoom: 18,
      zoomControl: true, attributionControl: false,
    })
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
    }).addTo(map)

    leafRef.current  = map
    layerRef.current = L.layerGroup().addTo(map)
  }, [])

  useEffect(() => {
    const L = window.L
    if (!L || !leafRef.current || !layerRef.current) return
    layerRef.current.clearLayers()

    const filtered = sessions.filter(s => {
      if (!s.lat || !s.lon) return false
      if (filter !== 'all' && s.skill_level !== filter) return false
      return true
    })

    filtered.forEach(s => {
      const color = SKILL_COLOR[s.skill_level] || '#6b7280'
      const marker = window.L.circleMarker([s.lat, s.lon], {
        radius: 7, fillColor: color, color: '#fff',
        weight: 1.5, opacity: 1, fillOpacity: 0.5,
      })
      marker.on('click', () => setSelected(s))
      layerRef.current.addLayer(marker)
    })
  }, [sessions, filter])

  const withCoords = sessions.filter(s => s.lat && s.lon)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', height: 'calc(100vh - 48px)' }}>

      {/* map fills full height */}
      <div style={{ position: 'relative' }}>
        {/* filter bar */}
        <div style={{
          position: 'absolute', top: 12, left: 60, zIndex: 1000,
          display: 'flex', gap: 6,
        }}>
          {[
            { id: 'all',          label: 'All' },
            { id: 'advanced',     label: 'Advanced',     color: '#ef4444' },
            { id: 'intermediate', label: 'Intermediate', color: '#f59e0b' },
            { id: 'script_kiddie',label: 'Script kiddie',color: '#3b82f6' },
          ].map(({ id, label, color }) => (
            <button key={id} onClick={() => setFilter(id)} style={{
              background: filter === id ? '#1a1d27' : 'rgba(13,15,20,.85)',
              border: `1px solid ${filter === id ? (color || '#3b82f6') : '#2a2d3a'}`,
              borderRadius: 6, padding: '4px 10px', fontSize: 11,
              color: filter === id ? (color || '#e2e4ec') : '#6b7280',
              cursor: 'pointer', backdropFilter: 'blur(4px)',
            }}>{label}</button>
          ))}
        </div>

        {/* stats overlay */}
        <div style={{
          position: 'absolute', bottom: 12, left: 12, zIndex: 1000,
          background: 'rgba(13,15,20,.9)', border: '1px solid #2a2d3a',
          borderRadius: 8, padding: '8px 14px',
          display: 'flex', gap: 20, fontSize: 12,
        }}>
          {[
            { label: 'On map',    value: withCoords.length,                              color: '#e2e4ec' },
            { label: 'Advanced',  value: sessions.filter(s => s.skill_level==='advanced').length,     color: '#ef4444' },
            { label: 'Intermediate', value: sessions.filter(s => s.skill_level==='intermediate').length, color: '#f59e0b' },
            { label: 'Script kiddie', value: sessions.filter(s => s.skill_level==='script_kiddie').length, color: '#3b82f6' },
          ].map(({ label, value, color }) => (
            <div key={label}>
              <div style={{ color, fontSize: 18, fontWeight: 600 }}>{value}</div>
              <div style={{ color: '#6b7280' }}>{label}</div>
            </div>
          ))}
        </div>

        <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      </div>

      {/* right panel — selected session or session list */}
      <div style={{
        background: '#0d0f14', borderLeft: '1px solid #2a2d3a',
        overflowY: 'auto', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #2a2d3a', fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1 }}>
          {selected ? 'Selected session' : `${withCoords.length} sessions on map`}
        </div>

        {selected ? (
          <SelectedPanel session={selected} onClose={() => setSelected(null)} />
        ) : (
          <SessionList sessions={sessions} onSelect={setSelected} />
        )}
      </div>
    </div>
  )
}

function SelectedPanel({ session: s, onClose }) {
  const color = SKILL_COLOR[s.skill_level] || '#6b7280'
  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontFamily: 'monospace', color: '#e2e4ec', fontSize: 14 }}>{s.id}</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: 18 }}>✕</button>
      </div>
      {[
        { label: 'IP',       value: s.ip },
        { label: 'Country',  value: [s.city, s.country].filter(Boolean).join(', ') },
        { label: 'ISP',      value: s.isp },
        { label: 'Commands', value: s.total_commands },
        { label: 'Duration', value: s.duration_s ? `${s.duration_s}s` : '—' },
      ].map(({ label, value }) => (
        <div key={label} style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 8, marginBottom: 8, fontSize: 13 }}>
          <span style={{ color: '#6b7280' }}>{label}</span>
          <span style={{ color: '#e2e4ec', wordBreak: 'break-all' }}>{value || '—'}</span>
        </div>
      ))}

      {s.skill_level && (
        <div style={{ marginTop: 16, padding: 12, background: '#1a1d27', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>AI profile</div>
          <div style={{ color, fontSize: 13, marginBottom: 4 }}>{s.skill_level.replace(/_/g,' ')}</div>
          <div style={{ color: '#a78bfa', fontSize: 13, marginBottom: 8 }}>{s.intent?.replace(/_/g,' ')}</div>
          {s.summary && <div style={{ color: '#9ca3af', fontSize: 12, lineHeight: 1.5 }}>{s.summary}</div>}
          {s.detected_tools?.length > 0 && (
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {s.detected_tools.map(t => (
                <span key={t} style={{ background: '#2a2d3a', color: '#9ca3af', fontSize: 11, padding: '2px 6px', borderRadius: 4 }}>{t}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SessionList({ sessions, onSelect }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {sessions.map(s => {
        const color = SKILL_COLOR[s.skill_level] || '#3b3f4a'
        return (
          <div key={s.id} onClick={() => onSelect(s)} style={{
            padding: '10px 16px', borderBottom: '1px solid #1a1d27',
            cursor: 'pointer', transition: 'background .1s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#1a1d27'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
              <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#e2e4ec' }}>{s.ip}</span>
              <span style={{ fontSize: 11, color: color }}>{s.skill_level?.replace(/_/g,' ') || 'unprofiled'}</span>
            </div>
            <div style={{ fontSize: 11, color: '#6b7280' }}>
              {s.country} · {s.total_commands} cmds
              {s.intent && <span style={{ color: '#a78bfa', marginLeft: 6 }}>{s.intent.replace(/_/g,' ')}</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}