export interface User {
  id: string
  username: string
  email: string | null
  is_active: boolean
  is_admin: boolean
  last_login_at: string | null
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export interface UpdateProfileRequest {
  email?: string | null
}
