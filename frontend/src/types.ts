// Mirrors backend/models.py. Keep the two in step.

export type Size = 'XS' | 'S' | 'M' | 'L' | 'XL' | 'XXL'
export const SIZES: Size[] = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
export type SearchSort = 'relevance' | 'price_asc' | 'price_desc' | 'name'

export type Category =
  | 'hoodie'
  | 'crewneck'
  | 't-shirt'
  | 'quarter-zip'
  | 'jacket'
  | 'performance'
  | 'other'

export type StockStatus = 'in_stock' | 'low' | 'sold_out'

export interface StockLevel {
  size: Size
  quantity: number
  status: StockStatus
}

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: Category
  short_description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  /** Problem 9: shown as chips on the card so nobody opens an item to learn their size is gone. */
  sizes_in_stock: Size[]
}

export interface ProductDetail extends ProductSummary {
  description: string
  search_tags: string[]
  stock: StockLevel[]
}

export interface ProductList {
  items: ProductSummary[]
  total: number
  categories: Category[]
}

export interface ProductQuery {
  q?: string
  category?: Category
  max_price?: number
  in_stock?: boolean
  sort?: SearchSort
}

export const SORT_LABELS: Record<SearchSort, string> = {
  relevance: 'Featured',
  price_asc: 'Price: low to high',
  price_desc: 'Price: high to low',
  name: 'Name A to Z',
}

export const CATEGORY_LABELS: Record<Category, string> = {
  hoodie: 'Hoodies',
  crewneck: 'Crewnecks',
  't-shirt': 'Tees',
  'quarter-zip': 'Quarter-zips',
  jacket: 'Jackets',
  performance: 'Performance',
  other: 'Other',
}

export const STOCK_LABELS: Record<StockStatus, string> = {
  in_stock: 'In stock',
  low: 'Only a few left',
  sold_out: 'Sold out',
}

// ------------------------------------------------------------------ auth

export type AuthProvider = 'password' | 'google' | 'github'

export interface UserPublic {
  id: number
  first_name: string
  last_name: string
  email: string
  auth_provider: AuthProvider
  created_at: string
  /** Problem 9: listed in the server's ADMIN_EMAILS; unlocks the restock queue. */
  is_admin: boolean
}

export interface AuthResponse {
  token: string
  expires_at: string
  user: UserPublic
}

export interface SignupRequest {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
  referral_code?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface DeleteMeResponse {
  ok: boolean
  deleted_messages: number
}

export interface ValidationIssue {
  loc: string[]
  msg: string
}

// ------------------------------------------------------------------ chat

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface PageContext {
  route: string
  product_id?: string
  product_name?: string
}

export interface ChatRequest {
  message: string
  history?: ChatTurn[]
  page?: PageContext
}

/** A page of this site the assistant offers (or opens, when `navigate` is true). Validated server-side. */
export interface PageLink {
  route: string
  label: string
  navigate: boolean
}

export interface ChatResponse {
  reply: string
  products: ProductSummary[]
  stopped_reason: string
  flagged: boolean
  signed_in: boolean
  go_to: PageLink | null
}

export interface ActivityItem {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: ProductSummary[]
  created_at: string
}

export interface ActivityResponse {
  items: ActivityItem[]
  total: number
}

export interface DeleteActivityResponse {
  ok: boolean
  deleted: number
}

// ------------------------------------------------------------------ hidden friends (Problem 9)

export interface Coupon {
  code: string
  discount_pct: number
  scope: 'one_item'
  found_character: string
  created_at: string
  redeemed_at: string | null
  already_claimed: boolean
}

export interface Reward {
  kind: 'free_item'
  code: string
  max_value_usd: number
  terms: string
  created_at: string
  redeemed_at: string | null
}

export interface HuntFriend {
  key: string
  name: string
  /** The page where this friend always hides until found; "/products/*" means any item page. */
  home_route: string
  riddle: string
  /** Daily sets: the day of the month this friend unlocks. */
  day: number | null
  available: boolean
  available_from: string
}

export interface HuntSeason {
  key: string
  name: string
  starts: string
  ends: string
  status: 'active' | 'coming' | 'past'
  daily: boolean
  today: string
  available_count: number
  friends: HuntFriend[]
}

export interface HuntMilestones {
  coupon_at: number
  coupon_pct: number
  lift_at: number
  lift_pct: number
  free_item_max_usd: number
  free_item_terms: string
  referral_credit_max: number
}

export interface HuntProgram {
  current_season: HuntSeason
  seasons: HuntSeason[]
  milestones: HuntMilestones
}

export interface FriendStatus {
  key: string
  name: string
  day: number | null
  available: boolean
  available_from: string
  found: boolean
  found_at: string | null
}

export type HuntEvent = 'new_find' | 'already_found' | 'coupon' | 'coupon_upgrade' | 'free_item'

export interface HuntProgress {
  season_key: string
  season_name: string
  friends: FriendStatus[]
  season_found: number
  season_total: number
  season_available: number
  total_finds: number
  referral_credits: number
  referral_code: string
  coupon: Coupon | null
  rewards: Reward[]
  unlocked: HuntEvent[]
  next_friend: string | null
  next_riddle: string | null
  milestones: HuntMilestones
}

// ------------------------------------------------------------------ restock requests (Problem 9)

export type RestockStatus = 'open' | 'ordered' | 'cancelled'

export interface RestockRequest {
  id: number
  product_id: string
  product_name: string
  size: Size
  status: RestockStatus
  created_at: string
  updated_at: string
}

export interface RestockList {
  items: RestockRequest[]
  total: number
}

export interface RestockStatusResponse {
  ok: boolean
  request: RestockRequest
}

export interface AdminRequester {
  request_id: number
  name: string
  email: string
  created_at: string
}

export interface AdminRestockGroup {
  product_id: string
  product_name: string
  size: Size
  open_count: number
  requested_by: AdminRequester[]
}

export interface AdminRestockQueue {
  groups: AdminRestockGroup[]
  total_open: number
  generated_at: string
}
