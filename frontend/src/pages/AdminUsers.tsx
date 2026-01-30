import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { usersApi } from '../services/api'
import { format } from 'date-fns'
import {
  Plus,
  Trash2,
  X,
  RefreshCw,
  Shield,
  ShieldOff,
  UserX,
  UserCheck,
} from 'lucide-react'

interface UserData {
  id: number
  username: string
  email: string
  is_active: boolean
  is_admin: boolean
  quota_limit: number
  quota_used: number
  created_at: string
  last_login: string | null
  api_key_count: number
}

export default function AdminUsers() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [editingUser, setEditingUser] = useState<UserData | null>(null)

  const { data: users, isLoading } = useQuery<UserData[]>({
    queryKey: ['admin-users'],
    queryFn: () => usersApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setShowCreateModal(false)
      toast.success('用户创建成功')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '创建失败')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: { id: number } & Partial<UserData>) =>
      usersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setEditingUser(null)
      toast.success('用户已更新')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '更新失败')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: usersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('用户已删除')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '删除失败')
    },
  })

  const resetQuotaMutation = useMutation({
    mutationFn: usersApi.resetQuota,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('配额已重置')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '重置失败')
    },
  })

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      username: formData.get('username') as string,
      email: formData.get('email') as string,
      password: formData.get('password') as string,
      is_admin: formData.get('is_admin') === 'true',
      quota_limit: parseFloat(formData.get('quota_limit') as string) || 100,
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
          <p className="text-gray-500 mt-1">管理系统用户</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>添加用户</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="stat-card">
          <p className="stat-label">总用户数</p>
          <p className="stat-value">{users?.length || 0}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">活跃用户</p>
          <p className="stat-value">
            {users?.filter((u) => u.is_active).length || 0}
          </p>
        </div>
        <div className="stat-card">
          <p className="stat-label">管理员</p>
          <p className="stat-value">
            {users?.filter((u) => u.is_admin).length || 0}
          </p>
        </div>
      </div>

      {/* Users Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  用户
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  状态
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  配额
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  API Keys
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  注册时间
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center">
                    <div className="w-8 h-8 border-2 border-primary-600/30 border-t-primary-600 rounded-full animate-spin mx-auto" />
                  </td>
                </tr>
              ) : users && users.length > 0 ? (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <div className="flex items-center space-x-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-medium ${
                          user.is_admin ? 'bg-purple-500' : 'bg-primary-500'
                        }`}>
                          {user.username[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 flex items-center space-x-2">
                            <span>{user.username}</span>
                            {user.is_admin && (
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                                管理员
                              </span>
                            )}
                          </p>
                          <p className="text-sm text-gray-500">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      {user.is_active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          活跃
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          禁用
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-sm">
                        <p className="font-medium">
                          {user.quota_used.toFixed(2)} / {user.quota_limit === Infinity ? '∞' : user.quota_limit.toFixed(2)}
                        </p>
                        <div className="w-24 h-1.5 bg-gray-200 rounded-full mt-1">
                          <div
                            className="h-full bg-primary-500 rounded-full"
                            style={{
                              width: `${Math.min((user.quota_used / user.quota_limit) * 100, 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600">
                      {user.api_key_count}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600">
                      {format(new Date(user.created_at), 'yyyy-MM-dd')}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => updateMutation.mutate({
                            id: user.id,
                            is_active: !user.is_active,
                          })}
                          className={`p-1.5 rounded-lg transition-colors ${
                            user.is_active
                              ? 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                              : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                          }`}
                          title={user.is_active ? '禁用用户' : '启用用户'}
                        >
                          {user.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => updateMutation.mutate({
                            id: user.id,
                            is_admin: !user.is_admin,
                          })}
                          className={`p-1.5 rounded-lg transition-colors ${
                            user.is_admin
                              ? 'text-purple-600 hover:bg-purple-50'
                              : 'text-gray-400 hover:text-purple-600 hover:bg-purple-50'
                          }`}
                          title={user.is_admin ? '移除管理员' : '设为管理员'}
                        >
                          {user.is_admin ? <Shield className="w-4 h-4" /> : <ShieldOff className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => resetQuotaMutation.mutate(user.id)}
                          className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                          title="重置配额"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('确定要删除这个用户吗？此操作不可恢复。')) {
                              deleteMutation.mutate(user.id)
                            }
                          }}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="删除用户"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    暂无用户
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md animate-slide-up">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">添加用户</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  用户名 *
                </label>
                <input
                  type="text"
                  name="username"
                  className="input"
                  placeholder="请输入用户名"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  邮箱 *
                </label>
                <input
                  type="email"
                  name="email"
                  className="input"
                  placeholder="请输入邮箱"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  密码 *
                </label>
                <input
                  type="password"
                  name="password"
                  className="input"
                  placeholder="请输入密码"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  配额限制
                </label>
                <input
                  type="number"
                  name="quota_limit"
                  className="input"
                  defaultValue={100}
                  min={0}
                  step={0.01}
                />
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  name="is_admin"
                  value="true"
                  id="is_admin"
                  className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                />
                <label htmlFor="is_admin" className="text-sm font-medium text-gray-700">
                  设为管理员
                </label>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="btn-primary"
                >
                  {createMutation.isPending ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
