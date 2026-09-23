'use client';
import {useEffect, useState} from 'react';
import {api} from '@/lib/api';

export type PrivacyState = {erased_session_ids?:string[];notice_version:string; acknowledged:boolean; research_opt_in:boolean; last_erased_at:string|null; deletion_request:{id:string;status:string;created_at:string;completed_at:string|null}|null};

export function DataNotice() {
  return <><p>ThinkFirst saves your questions, attempts, AI replies, feedback, learning preferences, support reports, and activity times to your account. Support reports contain only text you choose to share with the operator. When you ask AI, the relevant conversation is sent to an AI service. Automatic fallback may send that context to another configured service.</p><p>Research sharing is optional and off by default. Turning it on includes your saved conversations and future activity in research exports, including written attempts and reflections. You can turn it off at any time for future exports. Previously downloaded copies cannot be recalled automatically.</p><p>Conversations stay until you request deletion in Settings. Deletion needs operator processing; account and usage records remain. Avoid entering sensitive personal information. Drafts are stored on this device, so use your own browser profile on shared computers.</p></>;
}

export function PrivacyWelcome({onDone}: {onDone:(state:PrivacyState)=>void}) {
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  return <section className="connection-state prose"><span className="eyebrow">YOUR DATA</span><h1>Before you begin</h1><DataNotice/><p>Continuing acknowledges this notice. Research sharing stays off; you can choose it later in Settings.</p><button className="primary" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{onDone(await api<PrivacyState>('/privacy',{research_opt_in:false,acknowledge_notice:true}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>{busy?'Saving…':'I understand · Continue'}</button>{error&&<p role="alert">{error}</p>}</section>;
}

export default function DataControls() {
  const [data,setData]=useState<PrivacyState|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [confirmation,setConfirmation]=useState('');
  async function load(){try{setData(await api<PrivacyState>('/privacy'));setError('');}catch(e){setError((e as Error).message);}}
  useEffect(()=>{void load();},[]);
  async function run(action:()=>Promise<void>){setBusy(true);setError('');setMessage('');try{await action();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  const pending=data?.deletion_request?.status==='pending';
  return <section aria-labelledby="data-controls"><h3 id="data-controls">Your data</h3><details><summary>What happens to my data?</summary><DataNotice/></details>{!data?<button className="secondary" onClick={load}>Load data choices</button>:<>
    <label className="preference-toggle"><input type="checkbox" checked={data.research_opt_in} disabled={busy||pending} onChange={e=>{const enabled=e.target.checked;const previous=data;setData({...data,research_opt_in:enabled});void run(async()=>{try{setData(await api<PrivacyState>('/privacy',{research_opt_in:enabled,acknowledge_notice:true}));setMessage(enabled?'Research sharing enabled.':'Research sharing is off. Future exports will exclude your conversations.');}catch(e){setData(previous);throw e;}});}}/>Include my conversations in research</label>
    <p>You can use ThinkFirst with research sharing off.</p>
    <button className="secondary" disabled={busy} onClick={()=>void run(async()=>{const exported=await api<unknown>('/privacy/export');const url=URL.createObjectURL(new Blob([JSON.stringify(exported,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='thinkfirst-my-data.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);setMessage('Your data export is ready. Keep the downloaded file private.');})}>Download my data</button>
    {pending?<p role="status">Deletion requested. New saves and AI requests are paused until the operator processes it. You can still read and download your data. Request reference: {data.deletion_request?.id}</p>:<details><summary>Delete my conversations</summary><p>This requests deletion of all your saved conversations, answers, attempts, titles, learning goal, language preference, and support reports. The operator must process the request; it is not immediate. Research sharing turns off now. Your login, usage accounting, and request record remain. Existing research downloads and retained backups require separate operator handling.</p>{data.deletion_request?.status==='completed'&&<p>Your previous deletion request was completed.</p>}<label htmlFor="deletion-confirmation">Type DELETE MY CONVERSATIONS to confirm</label><input id="deletion-confirmation" value={confirmation} onChange={e=>setConfirmation(e.target.value)} autoComplete="off"/><button className="secondary" disabled={busy||confirmation!=='DELETE MY CONVERSATIONS'} onClick={()=>void run(async()=>{setData(await api<PrivacyState>('/privacy/deletion',{confirmation}));setConfirmation('');setMessage('Deletion requested. Your conversations have not been deleted yet.');})}>Request conversation deletion</button></details>}
  </>}{message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}</section>;
}
