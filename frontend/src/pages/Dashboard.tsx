import { useQuery } from '@tanstack/react-query'
import { usageApi, keysApi } from '../services/api'
import { useAuthStore } from '../stores/auth'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  Activity,
  Key,
  Zap,
  TrendingUp,
  AlertCircle,
} from 'lucide-react'

const COLORS = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1']

export default function Dashboard() {
  const { user } = useAuthStore()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['usage-stats'],
    queryFn: () => usageApi.getStats(),
  })

  const { data: quota } = useQuery({
    queryKey: ['quota'],
    queryFn: () => usageApi.getQuota(),
  })

  const { data: keys } = useQuery({
    queryKey: ['keys'],
    queryFn: () => keysApi.list(),
  })

  const { data: dailyUsage } = useQuery({
    queryKey: ['daily-usage'],
    queryFn: () => usageApi.getDaily(14),
  })

  const { data: modelBreakdown } = useQuery({
    queryKey: ['model-breakdown'],
    queryFn: () => usageApi.getModels(),
  })

  const statCards = [
    {
      label: '总请求数',
      value: stats?.total_requests?.toLocaleString() || '0',
      icon: Activity,
      color: 'text-blue-600 bg-blue-100',
    },
    {
      label: 'API Keys',
      value: keys?.length?.toString() || '0',
      icon: Key,
      color: 'text-purple-600 bg-purple-100',
    },
    {
      label: '总 Tokens',
      value: stats?.total_tokens?.toLocaleString() || '0',
      icon: Zap,
      color: 'text-green-600 bg-green-100',
    },
    {
      label: '成功率',
      value: `${(stats?.success_rate || 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'text-amber-600 bg-amber-100',
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          欢迎回来，{user?.username}
        </h1>
        <p className="text-gray-500 mt-1">
          这是你的 API 使用概览
        </p>
      </div>

      {/* Quota Warning */}
      {quota && quota.quota_percentage > 80 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div>
            <p className="font-medium text-amber-800">配额警告</p>
            <p className="text-sm text-amber-600">
              你已使用 {quota.quota_percentage.toFixed(1)}% 的配额，请注意用量
            </p>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className="flex items-center justify-between">
              <div className={`p-2 rounded-lg ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-4">
              <p className="stat-value">{statsLoading ? '-' : stat.value}</p>
              <p className="stat-label">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quota Progress */}
      {quota && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">配额使用情况</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">已使用 / 总配额</span>
              <span className="font-medium">
                {quota.quota_used.toFixed(2)} / {quota.quota_limit === Infinity ? '无限' : quota.quota_limit.toFixed(2)}
              </span>
            </div>
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  quota.quota_percentage > 90
                    ? 'bg-red-500'
                    : quota.quota_percentage > 70
                    ? 'bg-amber-500'
                    : 'bg-primary-500'
                }`}
                style={{ width: `${Math.min(quota.quota_percentage, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Usage Chart */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">每日请求量</h3>
          <div className="h-64">
            {dailyUsage && dailyUsage.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyUsage}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => value.slice(5)}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="request_count" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                暂无数据
              </div>
            )}
          </div>
        </div>

        {/* Model Breakdown Chart */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">模型使用分布</h3>
          <div className="h-64">
            {modelBreakdown && modelBreakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modelBreakdown}
                    dataKey="request_count"
                    nameKey="model"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ model, percent }) =>
                      `${model?.slice(0, 15) || 'unknown'} (${(percent * 100).toFixed(0)}%)`
                    }
                    labelLine={false}
                  >
                    {modelBreakdown.map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                暂无数据
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
