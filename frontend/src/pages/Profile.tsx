import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { User as UserIcon, Key, LogOut, Shield, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import authApi from '@/lib/authApi'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'

export function Profile() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()

  // Password change state
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState(false)

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
        <h1 className="text-2xl sm:text-3xl font-bold">个人中心</h1>
        <p className="text-sm text-muted-foreground mt-1">
          管理您的个人信息和账户设置
        </p>
      </div>

      {/* User Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            账户信息
          </CardTitle>
          <CardDescription>您的基本账户信息</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                用户名
              </label>
              <p className="text-base mt-1">{user?.username}</p>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">
                电子邮箱
              </label>
              <p className="text-base mt-1">
                {user?.email || <span className="text-muted-foreground">未设置</span>}
              </p>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">
                账户状态
              </label>
              <div className="mt-1">
                {user?.is_active ? (
                  <span className="inline-flex items-center gap-1 text-green-600">
                    <Shield className="h-4 w-4" />
                    激活
                  </span>
                ) : (
                  <span className="text-red-600">已禁用</span>
                )}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">
                账户角色
              </label>
              <p className="text-base mt-1">
                {user?.is_admin ? (
                  <span className="text-blue-600 font-medium">管理员</span>
                ) : (
                  '普通用户'
                )}
              </p>
            </div>

            {user?.created_at && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  注册时间
                </label>
                <p className="text-base mt-1 flex items-center gap-1">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {new Date(user.created_at).toLocaleString('zh-CN')}
                </p>
              </div>
            )}

            {user?.last_login_at && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  最后登录
                </label>
                <p className="text-base mt-1 flex items-center gap-1">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {new Date(user.last_login_at).toLocaleString('zh-CN')}
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
            修改密码
          </CardTitle>
          <CardDescription>更改您的登录密码以保护账户安全</CardDescription>
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
                密码修改成功！
              </Alert>
            )}

            <div>
              <label className="text-sm font-medium mb-2 block">
                当前密码 *
              </label>
              <Input
                type="password"
                placeholder="请输入当前密码"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                disabled={changePasswordMutation.isPending}
                required
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                新密码 *
              </label>
              <Input
                type="password"
                placeholder="请输入新密码（至少6个字符）"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={changePasswordMutation.isPending}
                required
                minLength={6}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                确认新密码 *
              </label>
              <Input
                type="password"
                placeholder="请再次输入新密码"
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
              {changePasswordMutation.isPending ? '修改中...' : '修改密码'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Logout */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LogOut className="h-5 w-5" />
            退出登录
          </CardTitle>
          <CardDescription>
            退出当前账户并返回登录页面
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            退出登录
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
