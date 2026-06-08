/**
 * [INPUT]: 依赖 api.authenticate，接收 result/onReset props
 * [OUTPUT]: 渲染支付结果状态，含 3DS 模态框
 * [POS]: components 层，checkout 流程终态展示
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

import { useState } from 'react'
import { api } from '../api'

const STATUS_CONFIG = {
  succeeded:             { bg: 'bg-secondary/20',   border: 'border-secondary/50',   title: 'Payment Successful',    color: 'text-secondary-foreground' },
  payment_failed:        { bg: 'bg-destructive/15', border: 'border-destructive/40', title: 'Payment Failed',        color: 'text-foreground'           },
  requires_action:       { bg: 'bg-accent/60',      border: 'border-accent',         title: '3D Secure Required',    color: 'text-accent-foreground'    },
  requires_confirmation: { bg: 'bg-muted/40',       border: 'border-border',         title: 'Awaiting Confirmation', color: 'text-primary'               },
  canceled:              { bg: 'bg-muted/20',       border: 'border-border',         title: 'Payment Canceled',      color: 'text-muted-foreground'      },
  error:                 { bg: 'bg-destructive/15', border: 'border-destructive/40', title: 'Request Error',         color: 'text-foreground'            },
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
          <div className="mt-6 p-4 bg-accent/60 rounded-xl border border-accent">
            <p className="text-sm font-semibold text-accent-foreground mb-3 text-center">
              Simulating 3D Secure Challenge
            </p>
            <p className="text-xs text-accent-foreground/80 mb-4 text-center">
              Your bank requires additional verification. Choose the outcome:
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleAuth('success')}
                disabled={authLoading}
                className="flex-1 py-2 bg-secondary hover:opacity-90 disabled:opacity-50 text-secondary-foreground font-semibold rounded-lg text-sm transition"
              >
                {authLoading ? '...' : 'Approve'}
              </button>
              <button
                onClick={() => handleAuth('fail')}
                disabled={authLoading}
                className="flex-1 py-2 bg-destructive hover:opacity-90 disabled:opacity-50 text-destructive-foreground font-semibold rounded-lg text-sm transition"
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
