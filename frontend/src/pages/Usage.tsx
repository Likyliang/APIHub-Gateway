import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { usageApi } from '../services/api'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  Activity,
  Zap,
  Clock,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import { format, subDays } from 'date-fns'

interface UsageRecord {
  id: number
  request_id: string
  endpoint: string
  method: string
  model: string | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost: number
  status_code: number | null
  response_time_ms: number | null
  is_streaming: boolean
  is_success: boolean
  error_message: string | null
  created_at: string
}

export default function Usage() {
  const [dateRange, setDateRange] = useState('7d')
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart')

  const getDays = () => {
    switch (dateRange) {
      case '24h': return 1
      case '7d': return 7
      case '30d': return 30
      case '90d': return 90
      default: return 7
    }
  }

  const { data: stats } = useQuery({
    queryKey: ['usage-stats', dateRange],
    queryFn: () => {
      const endDate = new Date().toISOString()
      const startDate = subDays(new Date(), getDays()).toISOString()
      return usageApi.getStats(startDate, endDate)
    },
  })

  const { data: dailyUsage } = useQuery({
    queryKey: ['daily-usage', dateRange],
    queryFn: () => usageApi.getDaily(getDays()),
  })

  const { data: records, isLoading: recordsLoading } = useQuery<UsageRecord[]>({
    queryKey: ['usage-records'],
    queryFn: () => usageApi.getRecords(100),
  })

  const { data: modelBreakdown } = useQuery({
    queryKey: ['model-breakdown', dateRange],
    queryFn: () => {
      const endDate = new Date().toISOString()
      const startDate = subDays(new Date(), getDays()).toISOString()
      return usageApi.getModels(startDate, endDate)
    },
  })

  const statCards = [
    {
      label: '总请求',
      value: stats?.total_requests?.toLocaleString() || '0',
      icon: Activity,
      color: 'text-blue-600 bg-blue-100',
    },
    {
      label: '总 Tokens',
      value: stats?.total_tokens?.toLocaleString() || '0',
      icon: Zap,
      color: 'text-purple-600 bg-purple-100',
    },
    {
      label: '平均响应时间',
      value: `${(stats?.avg_response_time_ms || 0).toFixed(0)}ms`,
      icon: Clock,
      color: 'text-green-600 bg-green-100',
    },
    {
      label: '成功率',
      value: `${(stats?.success_rate || 100).toFixed(1)}%`,
      icon: stats?.success_rate >= 95 ? CheckCircle : XCircle,
      color: stats?.success_rate >= 95 ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100',
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">用量统计</h1>
          <p className="text-gray-500 mt-1">查看 API 使用详情</p>
        </div>
        <div className="flex items-center space-x-3">
          {/* Date Range Selector */}
          <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
            {['24h', '7d', '30d', '90d'].map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  dateRange === range
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          {/* View Mode Toggle */}
          <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('chart')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'chart'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              图表
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'table'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              明细
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
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

      {viewMode === 'chart' ? (
        <>
          {/* Usage Chart */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">请求趋势</h3>
            <div className="h-80">
              {dailyUsage && dailyUsage.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyUsage}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => format(new Date(value), 'MM/dd')}
                    />
                    <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                      }}
                      formatter={(value: number, name: string) => [
                        value.toLocaleString(),
                        name === 'request_count' ? '请求数' : 'Tokens',
                      ]}
                    />
                    <Legend
                      formatter={(value) =>
                        value === 'request_count' ? '请求数' : 'Tokens'
                      }
                    />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="request_count"
                      stroke="#0ea5e9"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="total_tokens"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400">
                  暂无数据
                </div>
              )}
            </div>
          </div>

          {/* Model Breakdown */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">模型使用统计</h3>
            <div className="h-64">
              {modelBreakdown && modelBreakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={modelBreakdown} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis
                      type="category"
                      dataKey="model"
                      tick={{ fontSize: 12 }}
                      width={150}
                      tickFormatter={(value) => value?.slice(0, 20) || 'unknown'}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar dataKey="request_count" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400">
                  暂无数据
                </div>
              )}
            </div>
          </div>
        </>
      ) : (
        /* Records Table */
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    时间
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    模型
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Tokens
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    响应时间
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    状态
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recordsLoading ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      加载中...
                    </td>
                  </tr>
                ) : records && records.length > 0 ? (
                  records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {format(new Date(record.created_at), 'MM-dd HH:mm:ss')}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {record.model || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {record.total_tokens.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {record.response_time_ms ? `${record.response_time_ms}ms` : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {record.is_success ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            成功
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            失败
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      暂无记录
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
