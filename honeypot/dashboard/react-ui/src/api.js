const BASE = 'http://13.37.71.4:5002'

export const fetchSessions = () =>
  fetch(`${BASE}/api/sessions`).then(r => r.json())

export const fetchStats = () =>
  fetch(`${BASE}/api/stats`).then(r => r.json())

export const fetchSessionDetail = (id) =>
  fetch(`${BASE}/api/sessions/${id}`).then(r => r.json())