import { useState, useEffect } from 'react'
import { fetchSessionDetail } from '../api'

const SKILL_COLOR = {
  script_kiddie: '#94a3b8',
  intermediate:  '#4ade80',
  advanced:      '#f87171',
}

export default function SessionModal({ sessionId, onClose }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetchSessionDetail(sessionId).then(setData)
  }, [sessionId])

  const onBackdrop = e => { if (e.target === e.currentTarget) onClose() }

  return (
    <div onClick={onBackdrop} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.75)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }}>
      <div style={{
        background: '#13161e', border: '1px solid #2a2d3a',
        borderRadius: 12, width: 660, maxHeight: '85vh',
        overflowY: 'auto', padding: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 500, color: '#e2e4ec' }}>Session {sessionId}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', fontSize: 20, cursor: 'pointer' }}>✕</button>
        </div>
        {!data
          ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>Loading…</div>
          : <SessionDetail data={data} />}
      </div>
    </div>
  )
}

function SessionDetail({ data }) {
  const s = data.session
  const profile = s.profile

  return (
    <>
      <Section title="Connection">
        {/* FIX: use s.ip not s.client_ip */}
        <KV label="IP"       value={s.ip || s.client_ip || '—'} mono />
        <KV label="Location" value={[s.city, s.country].filter(Boolean).join(', ') || '—'} />
        <KV label="ISP"      value={s.isp || '—'} />
        <KV label="Duration" value={s.duration_s ? `${s.duration_s}s` : '—'} />
        <KV label="Commands" value={s.total_commands} />
        <KV label="Auth attempts" value={s.total_auth_attempts} />
      </Section>

      {profile && (
        <Section title="AI profile">
          <KV label="Skill"   value={profile.skill_level?.replace(/_/g,' ')} color={SKILL_COLOR[profile.skill_level]} />
          <KV label="Intent"  value={profile.probable_intent?.replace(/_/g,' ')} color="#a78bfa" />
          <KV label="Tools"   value={(profile.detected_tools||[]).join(', ') || '—'} />
          <KV label="IOCs"    value={(profile.ioc||[]).join(', ') || 'none'} />
          <KV label="Action"  value={profile.defensive_action} />
          <KV label="Summary" value={profile.summary} muted />
          {/* confidence bar */}
          <div style={{ gridColumn: '1/-1', marginTop: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#6b7280', marginBottom: 4 }}>
              <span>Confidence</span>
              <span>{Math.round((profile.confidence || 0) * 100)}%</span>
            </div>
            <div style={{ height: 4, background: '#1a1d27', borderRadius: 2 }}>
              <div style={{
                height: 4, borderRadius: 2,
                width: `${(profile.confidence || 0) * 100}%`,
                background: profile.confidence > 0.7 ? '#10b981' : profile.confidence > 0.4 ? '#f59e0b' : '#ef4444',
                transition: 'width .4s ease',
              }} />
            </div>
          </div>
        </Section>
      )}

      {/* command timeline */}
      {data.commands.length > 0 && (
        <Section title={`Command timeline (${data.commands.length})`}>
          <CommandTimeline commands={data.commands} />
        </Section>
      )}

      <Section title={`Auth attempts (${data.auth_attempts.length})`}>
        <div style={{ background: '#1a1d27', borderRadius: 8, padding: 12, maxHeight: 140, overflowY: 'auto', fontFamily: 'monospace', fontSize: 12 }}>
          {data.auth_attempts.length
            ? data.auth_attempts.map((a, i) => (
                <div key={i} style={{ padding: '3px 0', borderBottom: '1px solid #2a2d3a', color: '#f9a8d4' }}>
                  {a.username} : {a.password}
                </div>
              ))
            : <span style={{ color: '#4b5563' }}>none</span>}
        </div>
      </Section>
    </>
  )
}

function CommandTimeline({ commands }) {
  const maxOffset = commands[commands.length - 1]?.offset_ms || 1
  return (
    <div style={{ background: '#1a1d27', borderRadius: 8, padding: 12, maxHeight: 240, overflowY: 'auto' }}>
      {commands.map((c, i) => {
        const pct = Math.round((c.offset_ms / maxOffset) * 100)
        return (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
              <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#a5f3fc' }}>{c.command}</span>
              <span style={{ fontSize: 11, color: '#4b5563' }}>{(c.offset_ms / 1000).toFixed(1)}s</span>
            </div>
            <div style={{ height: 3, background: '#2a2d3a', borderRadius: 2 }}>
              <div style={{ height: 3, borderRadius: 2, width: `${pct}%`, background: '#3b82f6' }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
        {title}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '5px 12px' }}>
        {children}
      </div>
    </div>
  )
}

function KV({ label, value, mono, color, muted }) {
  return (
    <>
      <span style={{ fontSize: 13, color: '#6b7280', alignSelf: 'start', paddingTop: 1 }}>{label}</span>
      <span style={{
        fontSize: 13,
        fontFamily: mono ? 'monospace' : 'inherit',
        color: color || (muted ? '#6b7280' : '#e2e4ec'),
        wordBreak: 'break-all',
      }}>{value ?? '—'}</span>
    </>
  )
}