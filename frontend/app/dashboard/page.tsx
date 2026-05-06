'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { teamsApi } from '@/lib/api'
import type { Team, User } from '@/types'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create team modal state
  const [showCreate, setShowCreate] = useState(false)
  const [newTeamName, setNewTeamName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.replace('/login'); return }

    const stored = localStorage.getItem('user')
    if (stored) setUser(JSON.parse(stored))

    teamsApi.list()
      .then(setTeams)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [router])

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  async function handleCreateTeam(e: React.FormEvent) {
    e.preventDefault()
    setCreateError('')
    setCreating(true)
    try {
      const team = await teamsApi.create(newTeamName.trim())
      setTeams(prev => [team, ...prev])
      setShowCreate(false)
      setNewTeamName('')
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create team')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen">
      {/* Top navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <span className="font-semibold text-sm">Task Management</span>
          </div>
          <div className="flex items-center gap-3">
            {user && <span className="text-sm text-gray-600">{user.name}</span>}
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold">My Teams</h2>
            <p className="text-sm text-gray-500 mt-0.5">Teams you&apos;re a member of</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg px-3 py-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Team
          </button>
        </div>

        {loading && (
          <div className="text-sm text-gray-500 py-12 text-center">Loading…</div>
        )}

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {!loading && teams.length === 0 && !error && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No teams yet.</p>
            <p className="text-sm mt-1">Create one to get started.</p>
          </div>
        )}

        {/* Team cards grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {teams.map(team => (
            <Link
              key={team.id}
              href={`/teams/${team.id}`}
              className="block bg-white border border-gray-200 rounded-xl p-5 hover:border-indigo-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start justify-between">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 font-semibold text-sm">
                  {team.name.charAt(0).toUpperCase()}
                </div>
                <svg className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mt-3">{team.name}</h3>
              <p className="text-sm text-gray-400 mt-1">
                {team.members.length} {team.members.length === 1 ? 'member' : 'members'}
              </p>
            </Link>
          ))}
        </div>
      </main>

      {/* Create team modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-4">New Team</h3>
            <form onSubmit={handleCreateTeam} className="space-y-4">
              {createError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {createError}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Team name</label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={newTeamName}
                  onChange={e => setNewTeamName(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="e.g. Engineering"
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setNewTeamName(''); setCreateError('') }}
                  className="text-sm text-gray-600 hover:text-gray-800 px-3 py-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTeamName.trim()}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
                >
                  {creating ? 'Creating…' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
