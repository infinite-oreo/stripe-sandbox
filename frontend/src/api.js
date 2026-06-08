/**
 * [INPUT]: 依赖 VITE_API_BASE_URL 环境变量
 * [OUTPUT]: 对外提供 api.createPI, api.confirmPI, api.authenticate, api.listPI, api.createRefund
 * [POS]: API 客户端层，集中管理所有后端调用
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(method, path, body) {
  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await resp.json()
  if (!resp.ok) throw { status: resp.status, ...data }
  return data
}

export const api = {
  createPI: (amount, currency) =>
    request('POST', '/v1/payment_intents', { amount, currency }),

  confirmPI: (piId, card) =>
    request('POST', `/v1/payment_intents/${piId}/confirm`, {
      payment_method_data: { type: 'card', card },
    }),

  authenticate: (piId, action) =>
    request('POST', `/v1/payment_intents/${piId}/authenticate`, { action }),

  listPI: (limit = 50) =>
    request('GET', `/v1/payment_intents?limit=${limit}`),

  cancelPI: (piId) =>
    request('POST', `/v1/payment_intents/${piId}/cancel`),

  createRefund: (piId, amount) =>
    request('POST', '/v1/refunds', { payment_intent: piId, ...(amount ? { amount } : {}) }),
}
