export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
let tokenProvider: (() => Promise<string | null>) | null = null;
export function setTokenProvider(provider: (() => Promise<string | null>) | null) { tokenProvider = provider; }
export async function api<T>(path: string, body?: unknown): Promise<T> {
  let token: string | null = null;
  try { token = await tokenProvider?.() ?? null; }
  catch { throw new ApiError('Sign-in could not be refreshed. Please sign in again.', 401); }
  let response: Response;
  try {
    response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${path}`, {
      method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
      headers: {'Content-Type': 'application/json', ...(token ? {Authorization: `Bearer ${token}`} : {})},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}), signal: AbortSignal.timeout(65000),
    });
  } catch { throw new ApiError('Could not reach ThinkFirst. Check your connection and try again.', 0); }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(typeof data.detail === 'string' ? data.detail : 'This request could not be saved. Please check your input.', response.status);
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
export type SessionData = {id: string; status: string; events: LogEvent[]; summary: Record<string, any>; experience?:'chat'|'guided'; mode?:ConversationMode; practice?:PracticeState};
export type SessionList = {id: string; domain: string; status: string; started_at: string; problem_text: string}[];
export type Rollup = {sessions_total: number; sessions_closed: number; ai_requests_7d: number; ai_requests_30d: number; ai_first_ratio: number | null; verification_rate: number | null; no_ai_completion_rate: number | null; evaluation_completion_rate: number | null; skip_rate: number | null; refreshed_at: string; trend: {week: string; ai_first_ratio: number | null; verification_rate: number | null; time_to_ai_seconds: number | null}[]};
