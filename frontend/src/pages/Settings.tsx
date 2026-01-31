import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import {
  User,
  Mail,
  Lock,
  Save,
  Shield,
  Key,
  AlertTriangle,
} from 'lucide-react'

export default function Settings() {
  const { user, updateUser, logout } = useAuthStore()
  const [activeTab, setActiveTab] = useState('profile')

  const [username, setUsername] = useState(user?.username || '')
  const [email, setEmail] = useState(user?.email || '')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const { data: quota } = useQuery({
    queryKey: ['quota'],
    queryFn: async () => {
      const res = await fetch('/api/usage/quota', {
        headers: {
          Authorization: `Bearer ${useAuthStore.getState().token}`,
        },
      })
      return res.json()
    },
  })

  const updateProfileMutation = useMutation({
    mutationFn: async (data: { username?: string; email?: string; password?: string }) => {
      const res = await api.put('/auth/me', data)
      return res.data
    },
    onSuccess: (data) => {
      // Update local state with new user info
      updateUser({
        username: data.username,
        email: data.email,
      })
      toast.success('个人资料已更新')
      // If username changed, user needs to re-login
      if (data.username !== user?.username) {
        toast.success('用户名已更改，请重新登录')
        setTimeout(() => {
          logout()
          window.location.href = '/login'
        }, 1500)
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '更新失败')
    },
  })

  const tabs = [
    { id: 'profile', label: '个人资料', icon: User },
    { id: 'security', label: '安全设置', icon: Shield },
    { id: 'api', label: 'API 配置', icon: Key },
  ]

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    const updates: { username?: string; email?: string } = {}

    if (username !== user?.username) {
      updates.username = username
    }
    if (email !== user?.email) {
      updates.email = email
    }

    if (Object.keys(updates).length === 0) {
      toast.error('没有需要更新的内容')
      return
    }

    updateProfileMutation.mutate(updates)
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error('两次输入的密码不一致')
      return
    }
    if (newPassword.length < 6) {
      toast.error('密码长度至少6位')
      return
    }

    updateProfileMutation.mutate({ password: newPassword })
    setNewPassword('')
    setConfirmPassword('')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">设置</h1>
        <p className="text-gray-500 mt-1">管理你的账户设置</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="lg:w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary-50 text-primary-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">个人资料</h2>
              <form onSubmit={handleUpdateProfile} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    用户名
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="input pl-10"
                      placeholder="输入新用户名"
                      minLength={3}
                      maxLength={50}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    修改用户名后需要重新登录
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    邮箱
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="input pl-10"
                    />
                  </div>
                </div>

                {user?.is_admin && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start space-x-3">
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-amber-800">安全建议</p>
                      <p className="text-sm text-amber-600 mt-1">
                        作为管理员，强烈建议您修改默认用户名和密码以提高安全性。
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={updateProfileMutation.isPending}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <Save className="w-4 h-4" />
                    <span>{updateProfileMutation.isPending ? '保存中...' : '保存更改'}</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">修改密码</h2>
              <form onSubmit={handleChangePassword} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    新密码
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="input pl-10"
                      placeholder="请输入新密码（至少6位）"
                      required
                      minLength={6}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    确认新密码
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="input pl-10"
                      placeholder="请再次输入新密码"
                      required
                    />
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={updateProfileMutation.isPending}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <Save className="w-4 h-4" />
                    <span>{updateProfileMutation.isPending ? '更新中...' : '更新密码'}</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="space-y-6">
              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">配额信息</h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">总配额</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {quota?.quota_limit === null || quota?.is_unlimited ? '无限' : quota?.quota_limit?.toFixed(2) || '0'}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">已使用</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {quota?.quota_used?.toFixed(2) || '0'}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">剩余</p>
                    <p className="text-2xl font-bold text-green-600">
                      {quota?.is_unlimited ? '无限' : quota?.quota_remaining?.toFixed(2) || '0'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">API 端点</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Base URL
                    </label>
                    <code className="block bg-gray-50 px-4 py-3 rounded-lg text-sm font-mono text-gray-800">
                      {window.location.origin}/v1
                    </code>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Chat Completions
                    </label>
                    <code className="block bg-gray-50 px-4 py-3 rounded-lg text-sm font-mono text-gray-800">
                      POST {window.location.origin}/v1/chat/completions
                    </code>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Models
                    </label>
                    <code className="block bg-gray-50 px-4 py-3 rounded-lg text-sm font-mono text-gray-800">
                      GET {window.location.origin}/v1/models
                    </code>
                  </div>
                </div>
              </div>

              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">使用示例</h2>
                <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                  <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
{`curl ${window.location.origin}/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
