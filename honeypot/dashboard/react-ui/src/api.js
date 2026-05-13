export const fetchSessions = () =>
  fetch('/api/sessions').then(r => r.json())

export const fetchStats = () =>
  fetch('/api/stats').then(r => r.json())

export const fetchSessionDetail = (id) =>
  fetch(`/api/sessions/${id}`).then(r => r.json())