import type { Task, Team, TeamMember, User } from '@/types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  // Session expired or invalid token → kick back to login
  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    throw new Error('Unauthenticated')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(body.detail ?? 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (data: { name: string; email: string; password: string }) =>
    req<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  login: (data: { email: string; password: string }) =>
    req<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  me: () => req<User>('/auth/me'),
}

// ── Teams ─────────────────────────────────────────────────────────────────────

export const teamsApi = {
  list: () => req<Team[]>('/teams'),

  get: (teamId: number) => req<Team>(`/teams/${teamId}`),

  create: (name: string) =>
    req<Team>('/teams', { method: 'POST', body: JSON.stringify({ name }) }),

  addMember: (teamId: number, userId: number) =>
    req<TeamMember>(`/teams/${teamId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }),
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export const tasksApi = {
  list: (teamId: number, status?: string, assigneeId?: number) => {
    const p = new URLSearchParams()
    if (status) p.set('status', status)
    if (assigneeId) p.set('assignee_id', String(assigneeId))
    const qs = p.toString() ? `?${p}` : ''
    return req<Task[]>(`/teams/${teamId}/tasks${qs}`)
  },

  create: (teamId: number, data: { title: string; description?: string; assignee_id?: number }) =>
    req<Task>(`/teams/${teamId}/tasks`, { method: 'POST', body: JSON.stringify(data) }),

  update: (taskId: number, data: Partial<{ title: string; description: string; status: string; assignee_id: number | null }>) =>
    req<Task>(`/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(data) }),

  delete: (taskId: number) => req<void>(`/tasks/${taskId}`, { method: 'DELETE' }),
}
