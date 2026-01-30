import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { paymentApi, usageApi } from '../services/api'
import {
  CreditCard,
  Wallet,
  Zap,
  Check,
  Crown,
  ExternalLink,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react'
import { format } from 'date-fns'

interface PricePlan {
  id: number
  name: string
  description: string | null
  price: number
  quota_amount: number
  is_popular: boolean
}

interface Order {
  order_no: string
  amount: number
  quota_amount: number
  method: string
  status: string
  pay_url: string | null
  created_at: string
}

interface PaymentRecord {
  id: number
  order_no: string
  amount: number
  quota_amount: number
  method: string
  status: string
  created_at: string
  paid_at: string | null
}

export default function Recharge() {
  const queryClient = useQueryClient()
  const [selectedPlan, setSelectedPlan] = useState<number | null>(null)
  const [paymentMethod, setPaymentMethod] = useState<'wechat' | 'alipay'>('alipay')
  const [currentOrder, setCurrentOrder] = useState<Order | null>(null)
  const [checkingOrder, setCheckingOrder] = useState(false)

  const { data: plans, isLoading: plansLoading } = useQuery<PricePlan[]>({
    queryKey: ['price-plans'],
    queryFn: () => paymentApi.getPlans(),
  })

  const { data: quota } = useQuery({
    queryKey: ['quota'],
    queryFn: () => usageApi.getQuota(),
  })

  const { data: history } = useQuery<PaymentRecord[]>({
    queryKey: ['payment-history'],
    queryFn: () => paymentApi.getHistory(),
  })

  const createOrderMutation = useMutation({
    mutationFn: () => paymentApi.createOrder(selectedPlan!, paymentMethod),
    onSuccess: (data) => {
      setCurrentOrder(data)
      // Open payment URL in new window
      if (data.pay_url) {
        window.open(data.pay_url, '_blank')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '创建订单失败')
    },
  })

  // Check order status periodically
  useEffect(() => {
    if (!currentOrder || currentOrder.status !== 'pending') return

    const interval = setInterval(async () => {
      setCheckingOrder(true)
      try {
        const order = await paymentApi.getOrderStatus(currentOrder.order_no)
        if (order.status === 'paid') {
          toast.success('支付成功！配额已到账')
          setCurrentOrder(null)
          queryClient.invalidateQueries({ queryKey: ['quota'] })
          queryClient.invalidateQueries({ queryKey: ['payment-history'] })
        } else if (order.status === 'expired') {
          toast.error('订单已过期')
          setCurrentOrder(null)
        }
      } finally {
        setCheckingOrder(false)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [currentOrder, queryClient])

  const handlePayment = () => {
    if (!selectedPlan) {
      toast.error('请选择套餐')
      return
    }
    createOrderMutation.mutate()
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'paid':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <CheckCircle className="w-3 h-3 mr-1" />
            已支付
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            <Clock className="w-3 h-3 mr-1" />
            待支付
          </span>
        )
      case 'expired':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            <XCircle className="w-3 h-3 mr-1" />
            已过期
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            {status}
          </span>
        )
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">充值中心</h1>
        <p className="text-gray-500 mt-1">购买配额以继续使用 API 服务</p>
      </div>

      {/* Current Quota */}
      <div className="card bg-gradient-to-r from-primary-500 to-primary-600 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-primary-100">当前配额</p>
            <p className="text-3xl font-bold mt-1">
              {quota?.quota_remaining?.toFixed(2) || '0'} 单位
            </p>
          </div>
          <Wallet className="w-12 h-12 text-primary-200" />
        </div>
        <div className="mt-4">
          <div className="flex justify-between text-sm text-primary-100">
            <span>已使用 {quota?.quota_used?.toFixed(2) || '0'}</span>
            <span>总配额 {quota?.quota_limit === Infinity ? '∞' : quota?.quota_limit?.toFixed(2) || '0'}</span>
          </div>
          <div className="h-2 bg-primary-400/50 rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-white rounded-full transition-all"
              style={{ width: `${Math.min(quota?.quota_percentage || 0, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Pending Order */}
      {currentOrder && currentOrder.status === 'pending' && (
        <div className="card border-2 border-yellow-200 bg-yellow-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Loader2 className="w-6 h-6 text-yellow-600 animate-spin" />
              <div>
                <p className="font-medium text-yellow-800">等待支付</p>
                <p className="text-sm text-yellow-600">
                  订单号: {currentOrder.order_no} | ¥{currentOrder.amount}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {currentOrder.pay_url && (
                <a
                  href={currentOrder.pay_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary flex items-center space-x-1"
                >
                  <span>去支付</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
              <button
                onClick={() => setCurrentOrder(null)}
                className="btn-secondary"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Price Plans */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">选择套餐</h2>
        {plansLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-primary-600/30 border-t-primary-600 rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans?.map((plan) => (
              <div
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={`relative card cursor-pointer transition-all hover:shadow-lg ${
                  selectedPlan === plan.id
                    ? 'ring-2 ring-primary-500 border-primary-500'
                    : 'hover:border-gray-300'
                }`}
              >
                {plan.is_popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-amber-400 to-orange-500 text-white shadow-sm">
                      <Crown className="w-3 h-3 mr-1" />
                      推荐
                    </span>
                  </div>
                )}

                <div className="text-center pt-4">
                  <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{plan.description}</p>

                  <div className="mt-4">
                    <span className="text-3xl font-bold text-gray-900">¥{plan.price}</span>
                  </div>

                  <div className="mt-4 flex items-center justify-center text-primary-600">
                    <Zap className="w-5 h-5 mr-1" />
                    <span className="font-medium">{plan.quota_amount} 配额单位</span>
                  </div>

                  {selectedPlan === plan.id && (
                    <div className="absolute top-3 right-3">
                      <div className="w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center">
                        <Check className="w-4 h-4 text-white" />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Payment Method */}
      {selectedPlan && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">支付方式</h2>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setPaymentMethod('alipay')}
              className={`p-4 rounded-lg border-2 transition-all flex items-center justify-center space-x-3 ${
                paymentMethod === 'alipay'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                支
              </div>
              <span className="font-medium">支付宝</span>
            </button>
            <button
              onClick={() => setPaymentMethod('wechat')}
              className={`p-4 rounded-lg border-2 transition-all flex items-center justify-center space-x-3 ${
                paymentMethod === 'wechat'
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                微
              </div>
              <span className="font-medium">微信支付</span>
            </button>
          </div>

          <div className="mt-6 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">应付金额</p>
              <p className="text-2xl font-bold text-gray-900">
                ¥{plans?.find((p) => p.id === selectedPlan)?.price || 0}
              </p>
            </div>
            <button
              onClick={handlePayment}
              disabled={createOrderMutation.isPending}
              className="btn-primary px-8 py-3 text-lg flex items-center space-x-2"
            >
              {createOrderMutation.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <CreditCard className="w-5 h-5" />
              )}
              <span>立即支付</span>
            </button>
          </div>
        </div>
      )}

      {/* Payment History */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">充值记录</h2>
        {history && history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    订单号
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    金额
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    配额
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    方式
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    状态
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    时间
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((record) => (
                  <tr key={record.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono text-gray-600">
                      {record.order_no}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      ¥{record.amount}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      +{record.quota_amount}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {record.method === 'alipay' ? '支付宝' : '微信'}
                    </td>
                    <td className="px-4 py-3">
                      {getStatusBadge(record.status)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {format(new Date(record.created_at), 'MM-dd HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            暂无充值记录
          </div>
        )}
      </div>
    </div>
  )
}
