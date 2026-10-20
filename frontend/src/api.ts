// The one typed client for the Campus Customs API. Base URL from VITE_API_URL.
import type {
  ActivityResponse,
  AdminRestockQueue,
  AuthResponse,
  ChatRequest,
  ChatResponse,
  DeleteActivityResponse,
  DeleteMeResponse,
  HuntProgram,
  HuntProgress,
  LoginRequest,
  ProductDetail,
  ProductList,
  ProductQuery,
  ProductSummary,
  RestockList,
  RestockStatusResponse,
  SignupRequest,
  Size,
  UserPublic,
  ValidationIssue,
} from './types'

const BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  issues: ValidationIssue[]

  constructor(status: number, message: string, issues: ValidationIssue[] = []) {
    super(message)
    this.status = status
    this.issues = issues
  }
}

interface RequestOptions {
  body?: unknown
  token?: string | null
}

async function send(method: 'GET' | 'POST' | 'DELETE', path: string, opts: RequestOptions, accept: string): Promise<Response> {
  const headers: Record<string, string> = { Accept: accept }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`

  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    })
  } catch {
    throw new ApiError(0, 'Could not reach the shop API. Is the back end running?')
  }

  if (!res.ok) {
    let message = res.statusText || `Request failed (${res.status})`
    let issues: ValidationIssue[] = []
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        issues = body.detail as ValidationIssue[]
        message = issues.map((i) => i.msg).join(' ')
      }
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, message, issues)
  }
  return res
}

async function request<T>(method: 'GET' | 'POST' | 'DELETE', path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(method, path, opts, 'application/json')
  return (await res.json()) as T
}

async function requestText(path: string, opts: RequestOptions = {}): Promise<string> {
  const res = await send('GET', path, opts, 'text/csv')
  return res.text()
}

export const api = {
  listProducts(query: ProductQuery = {}): Promise<ProductList> {
    const params = new URLSearchParams()
    if (query.q) params.set('q', query.q)
    if (query.category) params.set('category', query.category)
    if (query.max_price !== undefined) params.set('max_price', String(query.max_price))
    if (query.in_stock) params.set('in_stock', 'true')
    if (query.sort && query.sort !== 'relevance') params.set('sort', query.sort)
    const qs = params.toString()
    return request<ProductList>('GET', `/products${qs ? `?${qs}` : ''}`)
  },

  getProduct(productId: string): Promise<ProductDetail> {
    return request<ProductDetail>('GET', `/products/${encodeURIComponent(productId)}`)
  },

  imageUrl(product: Pick<ProductSummary, 'image_url'>): string {
    return `${BASE}${product.image_url}`
  },

  // Accounts. Passwords travel only in a POST body over the API, never in a URL or a log line.
  signup(body: SignupRequest): Promise<AuthResponse> {
    return request<AuthResponse>('POST', '/auth/signup', { body })
  },

  login(body: LoginRequest): Promise<AuthResponse> {
    return request<AuthResponse>('POST', '/auth/login', { body })
  },

  social(accessToken: string): Promise<AuthResponse> {
    return request<AuthResponse>('POST', '/auth/social', { body: { access_token: accessToken } })
  },

  me(token: string): Promise<UserPublic> {
    return request<UserPublic>('GET', '/me', { token })
  },

  deleteMe(token: string): Promise<DeleteMeResponse> {
    return request<DeleteMeResponse>('DELETE', '/me', { token })
  },

  // Hidden friends (Problem 9). The server owns the rules and issues every code; the client only reports a tap.
  hunt(): Promise<HuntProgram> {
    return request<HuntProgram>('GET', '/hunt')
  },

  myHunt(token: string): Promise<HuntProgress> {
    return request<HuntProgress>('GET', '/me/hunt', { token })
  },

  recordFind(token: string, season: string, character: string): Promise<HuntProgress> {
    return request<HuntProgress>('POST', '/me/hunt/finds', { token, body: { season, character } })
  },

  // Restock requests (Problem 9): the shopper's own rows, and the staff queue for admins.
  restockRequests(token: string): Promise<RestockList> {
    return request<RestockList>('GET', '/me/restock-requests', { token })
  },

  createRestock(token: string, productId: string, size: Size): Promise<RestockStatusResponse> {
    return request<RestockStatusResponse>('POST', '/me/restock-requests', { token, body: { product_id: productId, size } })
  },

  cancelRestock(token: string, requestId: number): Promise<RestockStatusResponse> {
    return request<RestockStatusResponse>('DELETE', `/me/restock-requests/${requestId}`, { token })
  },

  adminRestockQueue(token: string): Promise<AdminRestockQueue> {
    return request<AdminRestockQueue>('GET', '/admin/restock-requests', { token })
  },

  adminRestockCsv(token: string): Promise<string> {
    return requestText('/admin/restock-requests.csv', { token })
  },

  adminMarkOrdered(token: string, requestId: number): Promise<RestockStatusResponse> {
    return request<RestockStatusResponse>('POST', `/admin/restock-requests/${requestId}/ordered`, { token })
  },

  // The agent. Signed-in shoppers get server memory; guests send their recent turns back.
  chat(body: ChatRequest, token?: string | null): Promise<ChatResponse> {
    return request<ChatResponse>('POST', '/chat', { body, token })
  },

  activity(token: string): Promise<ActivityResponse> {
    return request<ActivityResponse>('GET', '/me/activity', { token })
  },

  deleteActivity(token: string): Promise<DeleteActivityResponse> {
    return request<DeleteActivityResponse>('DELETE', '/me/activity', { token })
  },
}

export function formatPrice(price: number): string {
  return `$${Number.isInteger(price) ? price.toFixed(0) : price.toFixed(2)}`
}

export function messageOf(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  return err instanceof ApiError ? err.message : fallback
}
