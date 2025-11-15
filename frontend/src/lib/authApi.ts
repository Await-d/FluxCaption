import axios, { type AxiosInstance } from 'axios'
import type {
  LoginRequest,
  TokenResponse,
  User,
  ChangePasswordRequest,
  UpdateProfileRequest,
} from '../types/auth'

/**
 * Auth API Client
 */
class AuthAPIClient {
  private client: AxiosInstance

  constructor(baseURL: string = '/api/auth') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000,
    })

    // Request interceptor for adding auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )
  }

  /**
   * Get auth token from localStorage
   */
  private getToken(): string | null {
    try {
      const authStorage = localStorage.getItem('auth-storage')
      if (authStorage) {
        const parsed = JSON.parse(authStorage)
        return parsed.state?.token || null
      }
    } catch {
      return null
    }
    return null
  }

  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const { data } = await this.client.post<TokenResponse>('/login', credentials)
    return data
  }

  async logout(): Promise<void> {
    await this.client.post('/logout')
  }

  async getProfile(): Promise<User> {
    const { data } = await this.client.get<User>('/me')
    return data
  }

  async updateProfile(updates: UpdateProfileRequest): Promise<User> {
    const { data } = await this.client.put<User>('/me', updates)
    return data
  }

  async changePassword(request: ChangePasswordRequest): Promise<{ message: string }> {
    const { data } = await this.client.post<{ message: string }>('/change-password', request)
    return data
  }
}

export const authApi = new AuthAPIClient()
export default authApi
