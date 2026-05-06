export interface User {
  id: number
  name: string
  email: string
  created_at: string
}

export interface TeamMember {
  user_id: number
  joined_at: string
  user: User
}

export interface Team {
  id: number
  name: string
  creator_id: number
  created_at: string
  members: TeamMember[]
}

export type TaskStatus = 'todo' | 'in_progress' | 'done'

export interface Task {
  id: number
  title: string
  description: string | null
  status: TaskStatus
  team_id: number
  creator_id: number
  assignee_id: number | null
  created_at: string
  updated_at: string
}
