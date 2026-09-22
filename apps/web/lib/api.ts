export class ApiError extends Error {
  constructor(message: string, public status: number, public requestId?: string) { super(message); }
}
let tokenProvider: (() => Promise<string | null>) | null = null;
export function setTokenProvider(provider: (() => Promise<string | null>) | null) { tokenProvider = provider; }
export async function api<T>(path: string, body?: unknown): Promise<T> {
  let token: string | null = null;
  try { token = await tokenProvider?.() ?? null; }
  catch { throw new ApiError('Sign-in could not be refreshed. Please sign in again.', 401); }
  let response: Response;
  try {
    response = await fetch(`${(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '')}${path}`, {
      method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
      headers: {'Content-Type': 'application/json', ...(token ? {Authorization: `Bearer ${token}`} : {})},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}), signal: AbortSignal.timeout(65000),
    });
  } catch { throw new ApiError('Could not reach ThinkFirst. Check your connection and try again.', 0); }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const reference = response.headers.get('X-Request-ID');
    const requestId = reference && /^[a-f0-9-]{36}$/.test(reference) ? reference : undefined;
    const message = typeof data.detail === 'string' ? data.detail : 'This request could not be saved. Please check your input.';
    throw new ApiError(message + (requestId && response.status >= 500 ? ` Reference: ${requestId}` : ''), response.status, requestId);
  }
  return response.json();
}
export type LogEvent = {id: string; event_type: string; created_at: string; payload: Record<string, any>};
export type ProviderName = 'auto' | 'gemini' | 'groq' | 'openrouter' | 'mistral' | 'cloudflare' | 'anthropic';
export type ProviderConfig = {id: ProviderName; provider: string; configured: boolean; model: string; key_env: string; model_env: string};
export type AIStatus = ProviderConfig & {message: string; providers: ProviderConfig[]; available: boolean; fallback_enabled: boolean; fallback_order: ProviderName[]};
export type ConversationMode = 'ask_ai' | 'try_myself';
export type AIUsage = {daily_limit:number; requests_used:number; requests_remaining:number; resets_at:string; workspace?:{
  accounted_tokens:number; daily_token_limit:number; estimated_or_reserved_usd:number; daily_budget_usd:number|null;
  dollar_budget_enabled:boolean; rate_ceiling_usd_per_million:number|null; provider_attempts:number;
  reported_tokens:number; attempts_without_usage:number; max_attempts:number;
}};
export type PracticeState = {eligible:boolean; answer_event_id:string|null; reminders_enabled:boolean; active:boolean; question:string; task:string};
export type ConversationOverview = {own_attempts:number;ai_questions:number;ai_answers:number;failed_requests:number;ai_reviews:number;initial_mode:ConversationMode;outcome:string;status_label:string;fingerprint:string;can_review:boolean};
export type SessionData = {answer_style?:'concise'|'detailed';id: string; status: string; events: LogEvent[]; summary: Record<string, any>; experience?:'chat'|'guided'; mode?:ConversationMode; practice?:PracticeState;title?:string;custom_title?:boolean;overview?:ConversationOverview};
export type HistoryItem = {id:string;title:string;custom_title:boolean;problem_text:string;domain:string;status:string;outcome:string;status_label:string;experience:'chat'|'guided';started_at:string};
export type HistoryPage = {items:HistoryItem[];total:number;offset:number;limit:number;has_more:boolean};
export type ProgressData = {trend?:Rollup['trend'];experience:'chat'|'guided';totals:{conversations:number;in_progress:number;completed:number;unfinished:number;own_attempts:number;ai_questions:number;ai_answers:number;failed_requests:number;ai_reviews:number;started_myself:number};modes:{own_only:number;ai_only:number;both:number;no_saved_work:number};weeks:{week:string;own_attempts:number;ai_answers:number}[];updated_at:string};
export type SessionList = {id: string; domain: string; status: string; started_at: string; problem_text: string}[];
export type Rollup = {sessions_total: number; sessions_closed: number; ai_requests_7d: number; ai_requests_30d: number; ai_first_ratio: number | null; verification_rate: number | null; no_ai_completion_rate: number | null; evaluation_completion_rate: number | null; skip_rate: number | null; refreshed_at: string; trend: {week: string; ai_first_ratio: number | null; verification_rate: number | null; time_to_ai_seconds: number | null}[]};
