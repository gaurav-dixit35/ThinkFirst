"use client";
import {useEffect,useRef,useState} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';
import {downloadConversation} from '@/lib/conversationExport';
import {api,LogEvent,SessionData} from '@/lib/api';
import {requestKey} from '@/lib/aiRequest';

export function EditQuestion({sessionId,event,disabled}:{sessionId:string;event:LogEvent;disabled:boolean}) {
  const router=useRouter();
  const [editing,setEditing]=useState(false),[text,setText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const request=useRef<{event_id:string;source_event_id:string;question:string}|null>(null);
  const button=useRef<HTMLButtonElement>(null);
  function close(){setEditing(false);setError('');requestAnimationFrame(()=>button.current?.focus());}
  return <div className="message-edit"><button ref={button} className="text-button" disabled={disabled||busy} onClick={()=>{setText(event.payload.problem_text||event.payload.followup_text);setEditing(true);}}>Edit question</button>{editing&&<form onSubmit={async e=>{
    e.preventDefault();if(!text.trim()||busy)return;setBusy(true);setError('');
    if(!request.current||request.current.question!==text.trim())request.current={event_id:crypto.randomUUID(),source_event_id:event.id,question:text.trim()};
    try {const next=await api<{id:string}>(`/sessions/${sessionId}/edit-question`,request.current);localStorage.setItem(requestKey(next.id),JSON.stringify({event_id:crypto.randomUUID(),session_id:next.id,tier:3,stream:true}));router.push(`/session/${next.id}`);} catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }}><label>Edit your question<textarea autoFocus rows={4} maxLength={20000} value={text} disabled={busy} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Escape'&&!busy)close();}}/></label><p className="field-help">This opens a separate conversation with the earlier context. Your original stays saved. One AI request will be used.</p><div className="button-row"><button className="primary" disabled={busy||!text.trim()}>Save edit and ask AI</button><button type="button" className="secondary" disabled={busy} onClick={close}>Cancel edit</button></div>{error&&<p role="alert">{error}</p>}</form>}</div>;
}

export default function ConversationTools({data,busy,reload,onMatches}:{data:SessionData;busy:boolean;reload:()=>Promise<void>;onMatches:(ids:string[])=>void}) {
  const [query,setQuery]=useState(''),[index,setIndex]=useState(0),[error,setError]=useState(''),[saving,setSaving]=useState(false),[confirm,setConfirm]=useState('');
  const field=useRef<HTMLInputElement>(null),details=useRef<HTMLDetailsElement>(null);
  const ids=data.events.filter(e=>['session_started','attempt_submitted','ai_hint_requested','ai_hint_delivered'].includes(e.event_type)&&[e.payload.problem_text,e.payload.attempt_text,e.payload.followup_text,e.payload.hint_text].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase())).map(e=>e.id);
  const matches=query.trim()?ids:[];
  useEffect(()=>{onMatches(matches);setIndex(0);},[query,data.events]);
  useEffect(()=>{const find=(e:KeyboardEvent)=>{if((e.ctrlKey||e.metaKey)&&e.key==='f'&&document.activeElement?.closest('.conversation-page')){e.preventDefault();if(details.current)details.current.open=true;field.current?.focus();}};window.addEventListener('keydown',find);return()=>window.removeEventListener('keydown',find);},[]);
  function go(n:number){if(!matches.length)return;const next=(n+matches.length)%matches.length;setIndex(next);const item=document.getElementById(`message-${matches[next]}`);item?.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});item?.focus({preventScroll:true});}
  async function run(action:()=>Promise<unknown>){setSaving(true);setError('');try{await action();await reload();}catch(e){setError((e as Error).message);}finally{setSaving(false);}}
  return <details className="conversation-tools" ref={details}><summary>Conversation tools{data.archived?' · Archived':''}</summary>
    <form className="conversation-search" onSubmit={e=>{e.preventDefault();go(index);}}><label htmlFor="conversation-search">Search this conversation</label><input ref={field} id="conversation-search" type="search" maxLength={200} value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==='Escape'){setQuery('');details.current?.querySelector('summary')?.focus();}}}/><div className="button-row"><button className="secondary" type="button" disabled={!matches.length} onClick={()=>go(index-1)}>Previous match</button><button className="secondary" type="button" disabled={!matches.length} onClick={()=>go(index+1)}>Next match</button><span role="status">{query.trim()?`${matches.length?index+1:0} of ${matches.length} matches`:''}</span></div></form>
    <button className="secondary" disabled={busy||saving||data.deletion_pending} onClick={()=>void run(()=>api(`/sessions/${data.id}/archive`,{archived:!data.archived}))}>{data.archived?'Restore from archive':'Archive conversation'}</button>
    <div className="button-row"><button className="secondary" onClick={()=>{try{downloadConversation(data);setError('');}catch{setError('The conversation download could not start. Please try again.');}}}>Download conversation (.md)</button><Link className="text-button" href="/support">Report a problem</Link></div><p className="field-help">The download contains saved messages and retry attempts. Unsent drafts and partial AI previews are not included. Keep the file private.</p>
    <details><summary>Delete this conversation</summary><p>This requests permanent deletion by the operator. It pauses new saves here and moves this conversation to Awaiting deletion. Other conversations, including edited copies, are separate. Usage records remain.</p>{data.deletion_pending?<p role="status">Deletion requested. Operator processing is still pending.</p>:<><label>Type DELETE THIS CONVERSATION<input value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="off"/></label><button className="secondary" disabled={busy||saving||confirm!=='DELETE THIS CONVERSATION'} onClick={()=>void run(()=>api(`/sessions/${data.id}/deletion`,{confirmation:confirm}))}>Request deletion</button></>}</details>{error&&<p role="alert">{error}</p>}
  </details>;
}
