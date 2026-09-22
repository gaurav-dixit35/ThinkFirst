'use client';
import {useEffect,useState} from 'react';
import {api,AIUsage} from '@/lib/api';
export default function UsageSettings(){
  const [usage,setUsage]=useState<AIUsage|null>(null),[error,setError]=useState('');
  async function refresh(){try{setUsage(await api<AIUsage>('/ai/usage'));setError('');}catch(e){setError((e as Error).message);}}
  useEffect(()=>{void refresh();},[]);
  return <>{usage?<><div className="allowance-heading"><strong>{usage.requests_remaining}</strong><span>of {usage.daily_limit} AI requests left today</span></div><progress aria-label="AI requests used today" value={usage.requests_used} max={usage.daily_limit}/><p className="field-help">Resets {new Date(usage.resets_at).toLocaleString()}. Answers, hints and new AI reviews use this allowance. Reading saved work and thinking for yourself do not.</p><p>Shared service limits may also apply. Automatic provider fallback is part of the same request.</p></>:<p>Loading allowance…</p>}<button className="text-button" onClick={refresh}>Refresh allowance</button>{error&&<p role="alert">{error}</p>}</>;
}
