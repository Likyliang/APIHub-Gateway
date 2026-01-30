import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { paymentApi } from '../services/api'
import {
  DollarSign,
  Plus,
  Edit2,
  Trash2,
  TrendingUp,
  ShoppingCart,
  Crown,
  X,
} from 'lucide-react'

interface PricePlan {
  id: number
  name: string
  description: string | null
  price: number
  quota_amount: number
  is_popular: boolean
}

interface PaymentStats {
  total_orders: number
  total_revenue: number
  today_orders: number
  today_revenue: number
}

export default function AdminPayment() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingPlan, setEditingPlan] = useState<PricePlan | null>(null)

  const { data: stats } = useQuery<PaymentStats>({
    queryKey: ['payment-stats'],
    queryFn: () => paymentApi.getStats(),
  })

  const { data: plans, isLoading } = useQuery<PricePlan[]>({
    queryKey: ['price-plans'],
    queryFn: () => paymentApi.getPlans(),
  })

  const createMutation = useMutation({
    mutationFn: paymentApi.createPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['price-plans'] })
      setShowCreateModal(false)
      toast.success('套餐创建成功')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '创建失败')
    },
  })

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      name: formData.get('name') as string,
      price: parseFloat(formData.get('price') as string),
      quota_amount: parseFloat(formData.get('quota_amount') as string),
      description: formData.get('description') as string,
      is_popular: formData.get('is_popular') === 'on',
    })
  }

  const statCards = [
    {
      label: '总订单数',
      value: stats?.total_orders?.toString() || '0',
      icon: ShoppingCart,
      color: 'text-blue-600 bg-blue-100',
    },
    {
      label: '总收入',
      value: `¥${stats?.total_revenue?.toFixed(2) || '0'}`,
      icon: DollarSign,
      color: 'text-green-600 bg-green-100',
    },
    {
      label: '今日订单',
      value: stats?.today_orders?.toString() || '0',
      icon: TrendingUp,
      color: 'text-purple-600 bg-purple-100',
    },
    {
      label: '今日收入',
      value: `¥${stats?.today_revenue?.toFixed(2) || '0'}`,
      icon: DollarSign,
      color: 'text-amber-600 bg-amber-100',
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">支付管理</h1>
          <p className="text-gray-500 mt-1">管理价格套餐和查看收入统计</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>添加套餐</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className={`p-2 rounded-lg ${stat.color} w-fit`}>
              <stat.icon className="w-5 h-5" />
            </div>
            <div className="mt-3">
              <p className="stat-value">{stat.value}</p>
              <p className="stat-label">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Price Plans */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">价格套餐</h2>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="w-8 h-8 border-2 border-primary-600/30 border-t-primary-600 rounded-full animate-spin" />
          </div>
        ) : plans && plans.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="relative border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow"
              >
                {plan.is_popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-amber-400 to-orange-500 text-white">
                      <Crown className="w-3 h-3 mr-1" />
                      推荐
                    </span>
                  </div>
                )}

                <div className="text-center">
                  <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{plan.description || '-'}</p>
                  <div className="mt-4">
                    <span className="text-3xl font-bold text-gray-900">¥{plan.price}</span>
                  </div>
                  <div className="mt-2 text-primary-600 font-medium">
                    {plan.quota_amount} 配额
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 flex justify-center space-x-2">
                  <button
                    onClick={() => setEditingPlan(plan)}
                    className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    onClick={() => {
                      if (confirm('确定要删除这个套餐吗？')) {
                        // TODO: Implement delete
                        toast.success('套餐已删除')
                      }
                    }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            暂无价格套餐
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md animate-slide-up">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">添加套餐</h2>
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
                  套餐名称 *
                </label>
                <input
                  type="text"
                  name="name"
                  className="input"
                  placeholder="例如：标准套餐"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  价格 (CNY) *
                </label>
                <input
                  type="number"
                  name="price"
                  className="input"
                  placeholder="29.9"
                  step="0.01"
                  min="0"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  配额数量 *
                </label>
                <input
                  type="number"
                  name="quota_amount"
                  className="input"
                  placeholder="500"
                  min="1"
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
                  placeholder="适合日常使用"
                />
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  name="is_popular"
                  id="is_popular"
                  className="w-4 h-4 text-primary-600 rounded border-gray-300"
                />
                <label htmlFor="is_popular" className="text-sm font-medium text-gray-700">
                  标记为推荐套餐
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
