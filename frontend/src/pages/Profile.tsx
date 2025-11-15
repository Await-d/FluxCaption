import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { User as UserIcon, Key, LogOut, Shield, Clock, Edit2, Check, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import authApi from '@/lib/authApi'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'

export function Profile() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, clearAuth, updateUser } = useAuthStore()

  // Username edit state
  const [isEditingUsername, setIsEditingUsername] = useState(false)
  const [newUsername, setNewUsername] = useState(user?.username || '')
  const [usernameError, setUsernameError] = useState<string | null>(null)
  const [usernameSuccess, setUsernameSuccess] = useState(false)

  // Password change state
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState(false)

  // Username update mutation
  const updateUsernameMutation = useMutation({
    mutationFn: () =>
      authApi.updateProfile({
        username: newUsername,
      }),
    onSuccess: (updatedUser) => {
      updateUser(updatedUser)
      setUsernameSuccess(true)
      setUsernameError(null)
      setIsEditingUsername(false)
      setTimeout(() => setUsernameSuccess(false), 3000)
    },
    onError: (err: any) => {
      setUsernameError(err.response?.data?.detail || err.message || t('profile.usernameUpdateFailed'))
      setUsernameSuccess(false)
    },
  })

  // Password change mutation
  const changePasswordMutation = useMutation({
    mutationFn: () =>
      authApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
      }),
    onSuccess: () => {
      setPasswordSuccess(true)
      setPasswordError(null)
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPasswordSuccess(false), 5000)
    },
    onError: (err: any) => {
      setPasswordError(err.detail || err.message || t('profile.changePasswordFailed'))
      setPasswordSuccess(false)
    },
  })

  const handleUpdateUsername = () => {
    setUsernameError(null)
    setUsernameSuccess(false)

    // Validation
    if (!newUsername.trim()) {
      setUsernameError(t('profile.usernameEmpty'))
      return
    }

    if (newUsername.trim().length < 3) {
      setUsernameError(t('profile.usernameTooShort'))
      return
    }

    if (newUsername === user?.username) {
      setIsEditingUsername(false)
      return
    }

    updateUsernameMutation.mutate()
  }

  const handleCancelUsernameEdit = () => {
    setNewUsername(user?.username || '')
    setIsEditingUsername(false)
    setUsernameError(null)
  }

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(false)

    // Validation
    if (newPassword.length < 6) {
      setPasswordError(t('profile.passwordTooShort'))
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError(t('profile.passwordMismatch'))
      return
    }

    changePasswordMutation.mutate()
  }

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold">{t('profile.title')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t('profile.subtitle')}
        </p>
      </div>

      {/* User Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            {t('profile.accountInfo')}
          </CardTitle>
          <CardDescription>{t('profile.accountInfoDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {usernameSuccess && (
            <Alert className="text-sm bg-green-50 border-green-200 text-green-800">
              <Check className="h-4 w-4 text-green-600" />
              {t('profile.usernameUpdateSuccess')}
            </Alert>
          )}

          {usernameError && (
            <Alert variant="destructive" className="text-sm">
              {usernameError}
            </Alert>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                {t('profile.username')}
              </label>
              {isEditingUsername ? (
                <div className="mt-1 flex gap-2">
                  <Input
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    disabled={updateUsernameMutation.isPending}
                    placeholder={t('profile.usernamePlaceholder')}
                    className="flex-1"
                  />
                  <Button
                    size="sm"
                    onClick={handleUpdateUsername}
                    disabled={updateUsernameMutation.isPending || !newUsername.trim()}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCancelUsernameEdit}
                    disabled={updateUsernameMutation.isPending}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="mt-1 flex items-center gap-2">
                  <p className="text-base">{user?.username}</p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditingUsername(true)}
                  >
                    <Edit2 className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">
                {t('profile.email')}
              </label>
              <p className="text-base mt-1">
                {user?.email || <span className="text-muted-foreground">{t('profile.emailNotSet')}</span>}
              </p>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">
                {t('profile.accountStatus')}
              </label>
              <div className="mt-1">
                {user?.is_active ? (
                  <span className="inline-flex items-center gap-1 text-green-600">
                    <Shield className="h-4 w-4" />
                    {t('profile.active')}
                  </span>
                ) : (
                  <span className="text-red-600">{t('profile.disabled')}</span>
                )}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">
                {t('profile.accountRole')}
              </label>
              <p className="text-base mt-1">
                {user?.is_admin ? (
                  <span className="text-blue-600 font-medium">{t('profile.admin')}</span>
                ) : (
                  t('profile.regularUser')
                )}
              </p>
            </div>

            {user?.created_at && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  {t('profile.registrationTime')}
                </label>
                <p className="text-base mt-1 flex items-center gap-1">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {new Date(user.created_at).toLocaleString(i18n.language)}
                </p>
              </div>
            )}

            {user?.last_login_at && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  {t('profile.lastLogin')}
                </label>
                <p className="text-base mt-1 flex items-center gap-1">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {new Date(user.last_login_at).toLocaleString(i18n.language)}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            {t('profile.changePassword')}
          </CardTitle>
          <CardDescription>{t('profile.changePasswordDesc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            {passwordError && (
              <Alert variant="destructive" className="text-sm">
                {passwordError}
              </Alert>
            )}

            {passwordSuccess && (
              <Alert className="text-sm bg-green-50 border-green-200 text-green-800">
                {t('profile.passwordChangeSuccess')}
              </Alert>
            )}

            <div>
              <label className="text-sm font-medium mb-2 block">
                {t('profile.currentPassword')} *
              </label>
              <Input
                type="password"
                placeholder={t('profile.currentPasswordPlaceholder')}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                disabled={changePasswordMutation.isPending}
                required
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                {t('profile.newPassword')} *
              </label>
              <Input
                type="password"
                placeholder={t('profile.newPasswordPlaceholder')}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={changePasswordMutation.isPending}
                required
                minLength={6}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                {t('profile.confirmNewPassword')} *
              </label>
              <Input
                type="password"
                placeholder={t('profile.confirmPasswordPlaceholder')}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={changePasswordMutation.isPending}
                required
              />
            </div>

            <Button
              type="submit"
              disabled={
                changePasswordMutation.isPending ||
                !oldPassword ||
                !newPassword ||
                !confirmPassword
              }
            >
              <Key className="mr-2 h-4 w-4" />
              {changePasswordMutation.isPending ? t('profile.changing') : t('profile.changePasswordButton')}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Logout */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LogOut className="h-5 w-5" />
            {t('profile.logout')}
          </CardTitle>
          <CardDescription>
            {t('profile.logoutDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            {t('profile.logoutButton')}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
