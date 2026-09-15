'use client';
import {useEffect, useState} from 'react';
import {api, AIStatus, ProviderName} from '@/lib/api';

export default function AIConnection({selected,onSelect,disabled=false}:{selected:ProviderName|null;onSelect:(name:ProviderName)=>void;disabled?:boolean}) {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function check() {
    setBusy(true); setError('');
    try {const value=await api<AIStatus>('/ai/status');setStatus(value);if(!selected)onSelect('auto');}
    catch(e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  useEffect(() => {void check();}, []);
  const current = status?.providers.find(p=>p.id===selected) || status;
  return <section aria-label="AI connection" className="saved-attempt">
    <strong>{status ? status.available ? 'AI assistance' : 'AI is not connected yet' : 'Checking AI configuration…'}</strong>
    <p>{status ? status.available ? 'Ask for help below. Your work and conversation stay saved.' : 'Add an AI provider key to the local .env file and restart the API. Cloudflare also needs an account ID. You can still save your own work.' : error || 'Checking whether this workspace can request AI help.'}</p>
    {status && <details><summary>AI setup details</summary><label className="field-label" htmlFor="ai-provider">Preferred AI provider</label><select id="ai-provider" disabled={disabled||busy} value={selected || 'auto'} onChange={e=>onSelect(e.target.value as ProviderName)}><option value="auto">Automatic</option>{status.providers.map(p=><option key={p.id} value={p.id}>{p.provider}{p.configured?'':' — needs configuration'}</option>)}</select><p>{status.fallback_enabled?'If a service fails, another configured service can answer with the same context.':'Automatic fallback is disabled in server configuration.'}</p><p className="field-help">{current?.provider}: {current?.model}. Configuration does not confirm key validity or available credits.</p></details>}
    {error && status && <p role="alert">{error}</p>}
    <button className="text-button" disabled={busy} onClick={check}>{busy ? 'Checking…' : 'Recheck AI setup'}</button>
  </section>;
}
