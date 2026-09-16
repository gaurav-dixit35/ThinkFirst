'use client';
import {useEffect,useState} from 'react';
import {api,AIStatus,AIUsage} from '@/lib/api';

export default function AISetup() {
  const [status,setStatus]=useState<AIStatus|null>(null);
  const [usage,setUsage]=useState<AIUsage|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  async function refresh() {
    setBusy(true);setError('');
    try {const [nextStatus,nextUsage]=await Promise.all([api<AIStatus>('/ai/status'),api<AIUsage>('/ai/usage')]);setStatus(nextStatus);setUsage(nextUsage);}
    catch(e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  useEffect(()=>{void refresh();},[]);
  return <details className="ai-setup"><summary>Workspace AI setup</summary>
    <p>Provider settings apply to this workspace. Keys stay on the server. After editing the local .env file, restart the API.</p>
    {status&&<><p>{status.fallback_enabled?'Automatic fallback is enabled.':'Automatic fallback is disabled.'} Preferred service: {status.provider}.</p>
      {status.providers.map(p=><div key={p.id} className="provider-row"><div><strong>{p.provider}</strong><small>{p.model}</small>{!p.configured&&<small>Needs {p.key_env}{p.id==='cloudflare'?' and CLOUDFLARE_ACCOUNT_ID':''}.</small>}</div><span>{p.configured?'Configured':'Not configured'}</span></div>)}
      <p>Configured means the required settings are present. It does not confirm available credit or a live connection.</p></>}
    {error&&<p role="alert">{error}</p>}
    {usage?.workspace&&<div className="usage-details"><h3>Today’s AI usage</h3>
      <p>{usage.workspace.provider_attempts} provider attempts · {usage.workspace.reported_tokens.toLocaleString()} reported tokens.</p>
      <p>{usage.workspace.accounted_tokens.toLocaleString()} of {usage.workspace.daily_token_limit.toLocaleString()} shared tokens accounted for, including reservations and {usage.workspace.attempts_without_usage} attempts with unknown usage. Up to {usage.workspace.max_attempts} services may be tried per question.</p>
      <p>{usage.workspace.dollar_budget_enabled?`Estimated or reserved spend: $${usage.workspace.estimated_or_reserved_usd.toFixed(4)} of $${usage.workspace.daily_budget_usd?.toFixed(2)}.`:'Dollar budget is not configured. Request and token limits are active.'}</p>
      <p>Dollar estimates require AI_GLOBAL_DAILY_BUDGET_USD and AI_MAX_USD_PER_MILLION_TOKENS in .env. The rate ceiling must cover every configured model. These estimates are not an invoice or a provider-side billing cap.</p>
    </div>}
    <button className="secondary" disabled={busy} onClick={()=>void refresh()}>{busy?'Checking…':'Refresh configuration'}</button>
  </details>;
}
