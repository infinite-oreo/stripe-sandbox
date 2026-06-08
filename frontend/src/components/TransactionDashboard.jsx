/**
 * [INPUT]: 依赖 api.listPI/createRefund，5s 轮询后端
 * [OUTPUT]: 渲染交易列表，支持退款操作
 * [POS]: components 层，运营侧数据视图
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const STATUS_BADGE = {
  succeeded:             'bg-green-100 text-green-800',
  refunded:              'bg-purple-100 text-purple-800',
  payment_failed:        'bg-red-100 text-red-800',
  requires_action:       'bg-yellow-100 text-yellow-800',
  requires_confirmation: 'bg-blue-100 text-blue-800',
  canceled:              'bg-gray-100 text-gray-600',
}

function fmt(amount, currency) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'usd' })
    .format(amount / 100)
}

function fmtDate(iso) {
  return new Date(iso).toLocaleString()
}

export default function TransactionDashboard() {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [refunding, setRefunding] = useState(null)
  const [refundError, setRefundError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const resp = await api.listPI(50)
      setTransactions(resp.data)
    } catch {
      // 静默失败，保留旧数据
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [refresh])

  async function handleRefund(pi) {
    setRefunding(pi.id)
    setRefundError(null)
    try {
      await api.createRefund(pi.id)
      await refresh()
    } catch (err) {
      setRefundError(err?.detail?.error?.message || err?.message || 'Refund failed')
    } finally {
      setRefunding(null)
    }
  }

  if (loading) return (
    <div className="text-center py-16 text-muted-foreground">Loading transactions...</div>
  )

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-foreground">Transaction Dashboard</h2>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-block w-2 h-2 bg-primary rounded-full animate-pulse"></span>
          Auto-refresh 5s
        </div>
      </div>

      {refundError && (
        <div className="mb-3 px-4 py-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg flex justify-between items-center">
          {refundError}
          <button onClick={() => setRefundError(null)} className="ml-4 text-red-400 hover:text-red-600 font-medium">✕</button>
        </div>
      )}

      {transactions.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground border-2 border-dashed border-border rounded-xl">
          No transactions yet. Make a payment above.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['ID', 'Amount', 'Currency', 'Status', 'Card', 'Created', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {transactions.map(tx => (
                <tr key={tx.id} className="hover:bg-muted/50 transition">
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground max-w-[140px] truncate" title={tx.id}>{tx.id}</td>
                  <td className="px-4 py-3 font-medium text-foreground">{fmt(tx.amount, tx.currency)}</td>
                  <td className="px-4 py-3 uppercase text-muted-foreground">{tx.currency}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${STATUS_BADGE[tx.status] || 'bg-muted text-muted-foreground'}`}>
                      {tx.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">
                    {tx.card_last4 ? `•••• ${tx.card_last4}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{fmtDate(tx.created_at)}</td>
                  <td className="px-4 py-3">
                    {tx.status === 'succeeded' && (
                      <button
                        onClick={() => handleRefund(tx)}
                        disabled={refunding === tx.id}
                        className="text-xs px-3 py-1 bg-orange-100 hover:bg-orange-200 text-orange-700 rounded-full font-medium transition disabled:opacity-50"
                      >
                        {refunding === tx.id ? 'Refunding...' : 'Refund'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
