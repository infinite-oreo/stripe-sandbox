/**
 * [INPUT]: 依赖 CheckoutForm, PaymentResult, TransactionDashboard
 * [OUTPUT]: 渲染顶层页面布局，管理 checkout 状态机
 * [POS]: 应用根组件，页面级路由和状态协调者
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

import { useState, useEffect } from 'react'
import CheckoutForm from './components/CheckoutForm'
import PaymentResult from './components/PaymentResult'
import TransactionDashboard from './components/TransactionDashboard'

function useDarkMode() {
  const [dark, setDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  return [dark, setDark]
}

export default function App() {
  const [result, setResult] = useState(null)
  const [dark, setDark] = useDarkMode()

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-bold text-sm">S</div>
          <span className="font-bold text-foreground">Stripe Mock</span>
          <span className="text-xs px-2 py-0.5 bg-accent text-primary rounded-full font-medium">Local Dev</span>
          <button
            onClick={() => setDark(d => !d)}
            className="ml-auto w-8 h-8 flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground transition text-base"
            aria-label="Toggle dark mode"
          >
            {dark ? '☀' : '☾'}
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex justify-center mb-12">
          {result ? (
            <PaymentResult result={result} onReset={() => setResult(null)} />
          ) : (
            <CheckoutForm onResult={setResult} />
          )}
        </div>
        <TransactionDashboard />
      </main>
    </div>
  )
}
