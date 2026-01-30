import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { keysApi } from '../services/api'
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Edit2,
  X,
  Check,
  AlertCircle,
} from 'lucide-react'
import { format } from 'date-fns'

interface ApiKey {
  id: number
  key: string
  plain_key?: string
  name: string
  description: string | null
  is_active: boolean
  rate_limit: number
  quota_limit: number | null
  quota_used: number
  total_requests: number
  total_tokens: number
  created_at: string
  last_used_at: string | null
}

export default function ApiKeys() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKeyData, setNewKeyData] = useState<ApiKey | null>(null)
  const [showKey, setShowKey] = useState<number | null>(null)
  const [editingKey, setEditingKey] = useState<ApiKey | null>(null)

  const { data: keys, isLoading } = useQuery<ApiKey[]>({
    queryKey: ['keys'],
    queryFn: () => keysApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: keysApi.create,
    onSuccess: (data) => {
      setNewKeyData(data)
      queryClient.invalidateQueries({ queryKey: ['keys'] })
      toast.success('API Key 创建成功')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '创建失败')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: keysApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keys'] })
      toast.success('API Key 已删除')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '删除失败')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: { id: number; name?: string; is_active?: boolean }) =>
      keysApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keys'] })
      setEditingKey(null)
      toast.success('API Key 已更新')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '更新失败')
    },
  })

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      rate_limit: parseInt(formData.get('rate_limit') as string) || 60,
    })
    setShowCreateModal(false)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('已复制到剪贴板')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-gray-500 mt-1">管理你的 API 密钥</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>创建 Key</span>
        </button>
      </div>

      {/* New Key Alert */}
      {newKeyData && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Key className="w-5 h-5 text-green-600 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-green-800">新 API Key 已创建</p>
              <p className="text-sm text-green-600 mt-1">
                请立即复制保存，此密钥仅显示一次
              </p>
              <div className="mt-3 flex items-center space-x-2">
                <code className="flex-1 bg-white px-3 py-2 rounded border border-green-200 font-mono text-sm break-all">
                  {newKeyData.plain_key}
                </code>
                <button
                  onClick={() => copyToClipboard(newKeyData.plain_key!)}
                  className="btn-secondary flex items-center space-x-1"
                >
                  <Copy className="w-4 h-4" />
                  <span>复制</span>
                </button>
              </div>
              <button
                onClick={() => setNewKeyData(null)}
                className="text-sm text-green-600 hover:text-green-700 mt-2"
              >
                我已保存，关闭提示
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Keys List */}
      {isLoading ? (
        <div className="card flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary-600/30 border-t-primary-600 rounded-full animate-spin" />
        </div>
      ) : keys && keys.length > 0 ? (
        <div className="space-y-4">
          {keys.map((key) => (
            <div key={key.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${key.is_active ? 'bg-green-100' : 'bg-gray-100'}`}>
                    <Key className={`w-5 h-5 ${key.is_active ? 'text-green-600' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    {editingKey?.id === key.id ? (
                      <input
                        type="text"
                        value={editingKey.name}
                        onChange={(e) => setEditingKey({ ...editingKey, name: e.target.value })}
                        className="input py-1 px-2 text-lg font-medium"
                        autoFocus
                      />
                    ) : (
                      <h3 className="font-medium text-gray-900">{key.name}</h3>
                    )}
                    <p className="text-sm text-gray-500">{key.description || '无描述'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {editingKey?.id === key.id ? (
                    <>
                      <button
                        onClick={() => updateMutation.mutate({ id: key.id, name: editingKey.name })}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setEditingKey(null)}
                        className="p-2 text-gray-400 hover:bg-gray-100 rounded-lg"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setEditingKey(key)}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('确定要删除这个 API Key 吗？')) {
                            deleteMutation.mutate(key.id)
                          }
                        }}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Key Value */}
              <div className="mt-4 flex items-center space-x-2">
                <code className="flex-1 bg-gray-50 px-3 py-2 rounded font-mono text-sm text-gray-600">
                  {showKey === key.id ? key.key : key.key.replace(/./g, '•')}
                </code>
                <button
                  onClick={() => setShowKey(showKey === key.id ? null : key.id)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  {showKey === key.id ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => copyToClipboard(key.key)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>

              {/* Stats */}
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">请求数</p>
                  <p className="font-medium">{key.total_requests.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">Tokens</p>
                  <p className="font-medium">{key.total_tokens.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">速率限制</p>
                  <p className="font-medium">{key.rate_limit}/分钟</p>
                </div>
                <div>
                  <p className="text-gray-500">最后使用</p>
                  <p className="font-medium">
                    {key.last_used_at
                      ? format(new Date(key.last_used_at), 'MM-dd HH:mm')
                      : '从未'}
                  </p>
                </div>
              </div>

              {/* Status Toggle */}
              <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                <span className={`text-sm ${key.is_active ? 'text-green-600' : 'text-gray-500'}`}>
                  {key.is_active ? '已启用' : '已禁用'}
                </span>
                <button
                  onClick={() => updateMutation.mutate({ id: key.id, is_active: !key.is_active })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    key.is_active ? 'bg-primary-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      key.is_active ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Key className="w-12 h-12 text-gray-300 mx-auto" />
          <p className="text-gray-500 mt-4">还没有 API Key</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary mt-4"
          >
            创建第一个 Key
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md animate-slide-up">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">创建 API Key</h2>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  名称 *
                </label>
                <input
                  type="text"
                  name="name"
                  className="input"
                  placeholder="例如：生产环境"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  描述
                </label>
                <input
                  type="text"
                  name="description"
                  className="input"
                  placeholder="可选描述信息"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  速率限制（每分钟请求数）
                </label>
                <input
                  type="number"
                  name="rate_limit"
                  className="input"
                  defaultValue={60}
                  min={1}
                  max={1000}
                />
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
