/**
 * [INPUT]: 依赖 api.createPI/confirmPI, onResult 回调
 * [OUTPUT]: 渲染收银台表单，触发支付流程
 * [POS]: components 层，用户支付入口
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

import { useState } from 'react'
import { api } from '../api'

const TEST_CARDS = [
  { label: 'Success',       number: '4242424242424242' },
  { label: 'Decline',       number: '4000000000000002' },
  { label: '3D Secure',     number: '4000002500003155' },
  { label: 'Insuf. Funds',  number: '4000000000009995' },
  { label: 'Slow (3s)',     number: '4000000000000077' },
]

function formatCardNumber(raw) {
  return raw.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim()
}

export default function CheckoutForm({ onResult }) {
  const [cardNumber, setCardNumber] = useState('')
  const [expiry, setExpiry] = useState('')
  const [cvc, setCvc] = useState('')
  const [amount, setAmount] = useState('1000')
  const [loading, setLoading] = useState(false)

  function fillCard(number) {
    setCardNumber(formatCardNumber(number))
    setExpiry('12/30')
    setCvc('123')
  }

  function parseExpiry(val) {
    const [mm, yy] = val.split('/')
    return { exp_month: parseInt(mm || '0'), exp_year: parseInt('20' + (yy || '0')) }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const pi = await api.createPI(parseInt(amount), 'usd')
      const { exp_month, exp_year } = parseExpiry(expiry)
      const result = await api.confirmPI(pi.id, {
        number: cardNumber.replace(/\s/g, ''),
        exp_month,
        exp_year,
        cvc,
      })
      onResult(result)
    } catch (err) {
      onResult({ status: 'error', error: err })
    } finally {
      setLoading(false)
    }
  }

  function handleExpiryChange(e) {
    let val = e.target.value.replace(/\D/g, '').slice(0, 4)
    if (val.length >= 3) val = val.slice(0, 2) + '/' + val.slice(2)
    setExpiry(val)
  }

  const inputCls = 'w-full px-4 py-2.5 bg-input border border-border rounded-lg focus:ring-2 focus:ring-ring focus:border-transparent outline-none text-foreground placeholder:text-muted-foreground'

  return (
    <form onSubmit={handleSubmit} className="bg-card rounded-2xl shadow p-8 max-w-md w-full border border-border">
      <h2 className="text-2xl font-bold text-foreground mb-2">Stripe Mock Checkout</h2>
      <p className="text-sm text-muted-foreground mb-6">Test payments locally — no real charges</p>

      {/* 快捷填卡 */}
      <div className="mb-5">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Quick-fill test cards</p>
        <div className="flex flex-wrap gap-2">
          {TEST_CARDS.map(card => (
            <button
              key={card.number}
              type="button"
              onClick={() => fillCard(card.number)}
              className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:bg-accent hover:border-primary hover:text-primary transition"
            >
              {card.label}
            </button>
          ))}
        </div>
      </div>

      {/* 金额 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-foreground mb-1">Amount (cents)</label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-medium">$</span>
          <input
            type="number" min="1" value={amount}
            onChange={e => setAmount(e.target.value)}
            className={`${inputCls} pl-8`}
            placeholder="1000"
          />
        </div>
      </div>

      {/* 卡号 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-foreground mb-1">Card Number</label>
        <input
          type="text" value={cardNumber} placeholder="4242 4242 4242 4242"
          onChange={e => setCardNumber(formatCardNumber(e.target.value))}
          className={`${inputCls} font-mono tracking-widest`}
        />
      </div>

      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <label className="block text-sm font-medium text-foreground mb-1">Expiry (MM/YY)</label>
          <input
            type="text" value={expiry} placeholder="12/30"
            onChange={handleExpiryChange}
            className={inputCls}
          />
        </div>
        <div className="w-28">
          <label className="block text-sm font-medium text-foreground mb-1">CVC</label>
          <input
            type="text" value={cvc} placeholder="123" maxLength={3}
            onChange={e => setCvc(e.target.value.replace(/\D/g, '').slice(0, 3))}
            className={inputCls}
          />
        </div>
      </div>

      <button
        type="submit" disabled={loading}
        className="w-full py-3 bg-primary hover:opacity-90 disabled:opacity-50 text-primary-foreground font-semibold rounded-lg transition"
      >
        {loading ? 'Processing...' : 'Pay Now'}
      </button>
    </form>
  )
}
