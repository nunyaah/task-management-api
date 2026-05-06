'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { teamsApi, tasksApi } from '@/lib/api'
import type { Task, TaskStatus, Team, User } from '@/types'

// ── Status helpers ─────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: 'Todo',
  in_progress: 'In Progress',
  done: 'Done',
}

const STATUS_BADGE: Record<TaskStatus, string> = {
  todo: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  done: 'bg-emerald-100 text-emerald-700',
}

const STATUS_DOT: Record<TaskStatus, string> = {
  todo: 'bg-gray-400',
  in_progress: 'bg-blue-500',
  done: 'bg-emerald-500',
}

// ── Page component ─────────────────────────────────────────────────────────────

export default function TeamPage() {
  const router = useRouter()
  const params = useParams()
  const teamId = Number(params.teamId)

  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [team, setTeam] = useState<Team | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Selected task for the detail panel
  const [selected, setSelected] = useState<Task | null>(null)
  const [taskError, setTaskError] = useState('')

  // New task modal
  const [showNewTask, setShowNewTask] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newAssignee, setNewAssignee] = useState('')
  const [creating, setCreating] = useState(false)
  const [newTaskError, setNewTaskError] = useState('')

  // Add member modal
  const [showAddMember, setShowAddMember] = useState(false)
  const [memberId, setMemberId] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [addMemberError, setAddMemberError] = useState('')

  // ── Data fetching ────────────────────────────────────────────────────────────

  const fetchTasks = useCallback(async () => {
    const filter = statusFilter === 'all' ? undefined : statusFilter
    const data = await tasksApi.list(teamId, filter)
    setTasks(data)
  }, [teamId, statusFilter])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.replace('/login'); return }

    const stored = localStorage.getItem('user')
    if (stored) setCurrentUser(JSON.parse(stored))

    Promise.all([teamsApi.get(teamId), tasksApi.list(teamId)])
      .then(([t, tk]) => { setTeam(t); setTasks(tk) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [teamId, router])

  // Re-fetch tasks whenever the status filter changes (skip the initial load)
  useEffect(() => {
    if (!loading) fetchTasks().catch(e => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter])

  // ── Task actions ─────────────────────────────────────────────────────────────

  async function handleStatusChange(task: Task, status: TaskStatus) {
    setTaskError('')
    try {
      const updated = await tasksApi.update(task.id, { status })
      setTasks(prev => prev.map(t => t.id === updated.id ? updated : t))
      setSelected(updated)
    } catch (err: unknown) {
      setTaskError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  async function handleDelete(task: Task) {
    if (!confirm(`Delete "${task.title}"? This cannot be undone.`)) return
    try {
      await tasksApi.delete(task.id)
      setTasks(prev => prev.filter(t => t.id !== task.id))
      setSelected(null)
    } catch (err: unknown) {
      setTaskError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  async function handleCreateTask(e: React.FormEvent) {
    e.preventDefault()
    setNewTaskError('')
    setCreating(true)
    try {
      const task = await tasksApi.create(teamId, {
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        assignee_id: newAssignee ? Number(newAssignee) : undefined,
      })
      setTasks(prev => [task, ...prev])
      setShowNewTask(false)
      setNewTitle(''); setNewDesc(''); setNewAssignee('')
    } catch (err: unknown) {
      setNewTaskError(err instanceof Error ? err.message : 'Failed to create task')
    } finally {
      setCreating(false)
    }
  }

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault()
    setAddMemberError('')
    setAddingMember(true)
    try {
      await teamsApi.addMember(teamId, Number(memberId))
      // Refresh team to get updated member list
      const updated = await teamsApi.get(teamId)
      setTeam(updated)
      setShowAddMember(false)
      setMemberId('')
    } catch (err: unknown) {
      setAddMemberError(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setAddingMember(false)
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function memberName(userId: number) {
    return team?.members.find(m => m.user_id === userId)?.user.name ?? `User #${userId}`
  }

  function canEditTask(task: Task) {
    return currentUser?.id === task.creator_id || currentUser?.id === task.assignee_id
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <Link href="/dashboard" className="text-sm text-indigo-600 hover:underline">← Back to dashboard</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Dashboard
            </Link>
            <span className="text-gray-300">/</span>
            <span className="text-sm font-medium">{team?.name}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAddMember(true)}
              className="text-sm border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-lg px-3 py-1.5 transition-colors"
            >
              + Add Member
            </button>
            <button
              onClick={() => setShowNewTask(true)}
              className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-3 py-1.5 transition-colors"
            >
              + New Task
            </button>
          </div>
        </div>
      </nav>

      {/* Body: tasks (left) + members (right) */}
      <div className="max-w-6xl mx-auto px-4 py-6 flex gap-6">

        {/* ── Tasks column ── */}
        <div className="flex-1 min-w-0">
          {/* Status filter tabs */}
          <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
            {(['all', 'todo', 'in_progress', 'done'] as const).map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`text-sm rounded-md px-3 py-1.5 transition-colors font-medium ${
                  statusFilter === s
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {s === 'all' ? 'All' : STATUS_LABELS[s as TaskStatus]}
              </button>
            ))}
          </div>

          {/* Task list */}
          {tasks.length === 0 ? (
            <div className="text-center py-12 text-gray-400 text-sm">
              No tasks {statusFilter !== 'all' ? `with status "${STATUS_LABELS[statusFilter as TaskStatus]}"` : ''}.
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map(task => (
                <button
                  key={task.id}
                  onClick={() => { setSelected(task); setTaskError('') }}
                  className={`w-full text-left bg-white border rounded-xl px-4 py-3 hover:border-indigo-300 hover:shadow-sm transition-all ${
                    selected?.id === task.id ? 'border-indigo-400 ring-1 ring-indigo-200' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[task.status]}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${STATUS_BADGE[task.status]}`}>
                          {STATUS_LABELS[task.status]}
                        </span>
                        {task.assignee_id && (
                          <span className="text-xs text-gray-400">
                            → {memberName(task.assignee_id)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Members column ── */}
        <div className="w-60 flex-shrink-0">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Members <span className="text-gray-400 font-normal">({team?.members.length})</span>
            </h3>
            <ul className="space-y-2">
              {team?.members.map(m => (
                <li key={m.user_id} className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 text-xs font-semibold flex items-center justify-center flex-shrink-0">
                    {m.user.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-gray-800 truncate">{m.user.name}</p>
                    {m.user_id === team.creator_id && (
                      <p className="text-xs text-gray-400">creator</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* User ID hint — needed because Add Member requires a user ID */}
          {currentUser && (
            <div className="mt-3 bg-gray-50 border border-gray-200 rounded-xl p-3">
              <p className="text-xs text-gray-500">Your user ID</p>
              <p className="text-sm font-mono font-medium text-gray-700 mt-0.5">{currentUser.id}</p>
              <p className="text-xs text-gray-400 mt-1">Share this with teammates so they can add you to their teams.</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Task detail panel (modal) ─────────────────────────────────────────── */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-start justify-between mb-4">
              <h3 className="font-semibold text-gray-900 pr-4">{selected.title}</h3>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {taskError && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
                {taskError}
              </div>
            )}

            {selected.description && (
              <p className="text-sm text-gray-600 mb-4">{selected.description}</p>
            )}

            {/* Status */}
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Status</p>
              {canEditTask(selected) ? (
                <div className="flex gap-2">
                  {(['todo', 'in_progress', 'done'] as TaskStatus[]).map(s => (
                    <button
                      key={s}
                      onClick={() => handleStatusChange(selected, s)}
                      className={`text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors ${
                        selected.status === s
                          ? STATUS_BADGE[s] + ' ring-1 ring-current'
                          : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }`}
                    >
                      {STATUS_LABELS[s]}
                    </button>
                  ))}
                </div>
              ) : (
                <span className={`text-xs px-2 py-1 rounded-md font-medium ${STATUS_BADGE[selected.status]}`}>
                  {STATUS_LABELS[selected.status]}
                </span>
              )}
            </div>

            {/* Meta */}
            <div className="space-y-1.5 text-sm text-gray-500 border-t border-gray-100 pt-4">
              <div className="flex justify-between">
                <span>Created by</span>
                <span className="text-gray-700">{memberName(selected.creator_id)}</span>
              </div>
              {selected.assignee_id && (
                <div className="flex justify-between">
                  <span>Assigned to</span>
                  <span className="text-gray-700">{memberName(selected.assignee_id)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>Created</span>
                <span>{new Date(selected.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            {/* Footer actions */}
            <div className="flex items-center justify-between mt-5 pt-4 border-t border-gray-100">
              {currentUser?.id === selected.creator_id ? (
                <button
                  onClick={() => handleDelete(selected)}
                  className="text-sm text-red-500 hover:text-red-700 transition-colors"
                >
                  Delete task
                </button>
              ) : (
                <span className="text-xs text-gray-400">
                  {canEditTask(selected) ? '' : 'You can only update tasks you created or are assigned to.'}
                </span>
              )}
              <button
                onClick={() => setSelected(null)}
                className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1.5 border border-gray-200 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── New task modal ────────────────────────────────────────────────────── */}
      {showNewTask && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold mb-4">New Task</h3>
            <form onSubmit={handleCreateTask} className="space-y-4">
              {newTaskError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {newTaskError}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="e.g. Fix login bug"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                  placeholder="Optional description…"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assign to</label>
                <select
                  value={newAssignee}
                  onChange={e => setNewAssignee(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
                >
                  <option value="">Unassigned</option>
                  {team?.members.map(m => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.user.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => { setShowNewTask(false); setNewTitle(''); setNewDesc(''); setNewAssignee(''); setNewTaskError('') }}
                  className="text-sm text-gray-600 hover:text-gray-800 px-3 py-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTitle.trim()}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
                >
                  {creating ? 'Creating…' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Add member modal ──────────────────────────────────────────────────── */}
      {showAddMember && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-1">Add Member</h3>
            <p className="text-sm text-gray-500 mb-4">
              Ask your teammate for their user ID. They can find it in the &quot;Your user ID&quot; card on this page.
            </p>
            <form onSubmit={handleAddMember} className="space-y-4">
              {addMemberError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {addMemberError}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">User ID</label>
                <input
                  type="number"
                  required
                  autoFocus
                  value={memberId}
                  onChange={e => setMemberId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="e.g. 2"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowAddMember(false); setMemberId(''); setAddMemberError('') }}
                  className="text-sm text-gray-600 hover:text-gray-800 px-3 py-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingMember || !memberId}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
                >
                  {addingMember ? 'Adding…' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
