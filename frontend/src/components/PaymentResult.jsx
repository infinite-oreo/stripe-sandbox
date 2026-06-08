/**
 * [INPUT]: 依赖 api.authenticate，接收 result/onReset props
 * [OUTPUT]: 渲染支付结果状态，含 3DS 模态框
 * [POS]: components 层，checkout 流程终态展示
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

import { useState } from 'react'
import { api } from '../api'

const STATUS_CONFIG = {
  succeeded:             { bg: 'bg-green-50',  border: 'border-green-200', title: 'Payment Successful',    color: 'text-green-700'  },
  payment_failed:        { bg: 'bg-red-50',    border: 'border-red-200',   title: 'Payment Failed',        color: 'text-red-700'    },
  requires_action:       { bg: 'bg-yellow-50', border: 'border-yellow-200',title: '3D Secure Required',    color: 'text-yellow-700' },
  requires_confirmation: { bg: 'bg-accent',    border: 'border-border',    title: 'Awaiting Confirmation', color: 'text-primary'    },
  canceled:              { bg: 'bg-muted',     border: 'border-border',    title: 'Payment Canceled',      color: 'text-muted-foreground' },
  error:                 { bg: 'bg-red-50',    border: 'border-red-200',   title: 'Request Error',         color: 'text-red-700'    },
}

export default function PaymentResult({ result, onReset }) {
  const [authLoading, setAuthLoading] = useState(false)
  const [finalResult, setFinalResult] = useState(result)

  const cfg = STATUS_CONFIG[finalResult?.status] || STATUS_CONFIG.error

  async function handleAuth(action) {
    setAuthLoading(true)
    try {
      const updated = await api.authenticate(result.id, action)
      setFinalResult(updated)
    } catch (err) {
      setFinalResult({ status: 'error', error: err })
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <div className="max-w-md w-full">
      <div className={`rounded-2xl border-2 ${cfg.bg} ${cfg.border} p-8 shadow-sm`}>
        <h2 className={`text-2xl font-bold text-center mb-2 ${cfg.color}`}>{cfg.title}</h2>

        {finalResult?.id && (
          <div className="mt-4 space-y-1 text-sm text-muted-foreground">
            <p><span className="font-medium text-foreground">ID:</span> {finalResult.id}</p>
            <p><span className="font-medium text-foreground">Amount:</span> {finalResult.amount} {finalResult.currency?.toUpperCase()}</p>
            {finalResult.card_last4 && (
              <p><span className="font-medium text-foreground">Card:</span> •••• {finalResult.card_last4}</p>
            )}
            {finalResult.error_message && (
              <p className="text-red-600"><span className="font-medium">Error:</span> {finalResult.error_message}</p>
            )}
          </div>
        )}

        {/* 3DS 操作区 */}
        {finalResult?.status === 'requires_action' && (
          <div className="mt-6 p-4 bg-yellow-100 rounded-xl border border-yellow-300">
            <p className="text-sm font-semibold text-yellow-800 mb-3 text-center">
              Simulating 3D Secure Challenge
            </p>
            <p className="text-xs text-yellow-700 mb-4 text-center">
              Your bank requires additional verification. Choose the outcome:
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleAuth('success')}
                disabled={authLoading}
                className="flex-1 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition"
              >
                {authLoading ? '...' : 'Approve'}
              </button>
              <button
                onClick={() => handleAuth('fail')}
                disabled={authLoading}
                className="flex-1 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition"
              >
                {authLoading ? '...' : 'Reject'}
              </button>
            </div>
          </div>
        )}
      </div>

      <button
        onClick={onReset}
        className="mt-4 w-full py-2.5 border-2 border-primary/30 text-primary hover:bg-accent font-medium rounded-lg transition"
      >
        New Payment
      </button>
    </div>
  )
}
