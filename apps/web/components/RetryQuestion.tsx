'use client';
import {useEffect,useState,useRef} from 'react';
import Link from 'next/link';
import {api} from '@/lib/api';
import {SavedDetail} from '@/lib/learning';
import {emitEvent,flushQueue} from '@/lib/eventClient';
import {useAttemptDraft} from '@/lib/useAttemptDraft';
import {useIdentity} from './Providers';
import AnswerContent from './AnswerContent';

export default function RetryQuestion({answerId}:{answerId:string}){
 const [data,setData]=useState<SavedDetail|null>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{let active=true;setData(null);setError('');void api<SavedDetail>(`/saved/${answerId}`).then(value=>{if(active)setData(value);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[answerId,retry]);
 if(!data)return <section className="learning-page"><h1>Revisit a question</h1>{error?<div className="error" role="alert">{error}<button onClick={()=>setRetry(n=>n+1)}>Retry loading</button></div>:<p role="status">Loading your saved question…</p>}<Link className="text-button" href="/saved">Back to Saved</Link></section>;
 return <Practice key={answerId} initial={data}/>;
}
function Practice({initial}:{initial:SavedDetail}){
 const [data,setData]=useState(initial),[revealed,setRevealed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const {attempt,setAttempt,storageError}=useAttemptDraft(`learning.${data.answer_id}.${data.session_id}`);
 const identity=useIdentity();
 const readonly=data.deletion_pending||identity?.privacy?.deletion_request?.status==='pending';
 const input=useRef<HTMLTextAreaElement>(null),comparison=useRef<HTMLElement>(null);
 const saving=useRef(false);
 useEffect(()=>{if(revealed)comparison.current?.focus();},[revealed]);
 async function save(){
  if(saving.current||!attempt.trim()||readonly)return;saving.current=true;setBusy(true);setError('');setNotice('');
  try{const text=attempt.trim();const eventId=await emitEvent(data.session_id,'learning_attempt_submitted',{answer_event_id:data.answer_id,attempt_text:text});setData(current=>current.attempts.some(entry=>entry.id===eventId)?current:{...current,attempts:[...current.attempts,{id:eventId,text,created_at:new Date().toISOString()}]});setAttempt('');setRevealed(true);setNotice('Your attempt is saved. Compare it with the earlier AI response.');const value=await api<SavedDetail>(`/saved/${data.answer_id}`);setData(value);}
  catch(e){setError((e as Error).message);}finally{saving.current=false;setBusy(false);}
 }
 async function sync(){if(saving.current)return;saving.current=true;setBusy(true);try{await flushQueue(data.session_id);const value=await api<SavedDetail>(`/saved/${data.answer_id}`);setData(value);if(attempt.trim()&&value.attempts.at(-1)?.text===attempt.trim()){setAttempt('');setRevealed(true);}setError('');setNotice('Saved attempts refreshed.');}catch(e){setError((e as Error).message);}finally{saving.current=false;setBusy(false);}}
 return <section className="learning-page"><Link className="text-button" href="/saved">← Back to Saved</Link><header><span className="eyebrow">A FRESH ATTEMPT</span><h1>What do you remember?</h1><p>Try the question in your own words, then compare. This uses no AI requests and does not change the original conversation.</p></header><div className="practice-question"><h2>Your saved question</h2><p>{data.question}</p><Link className="text-button" href={`/session/${data.session_id}#message-${data.answer_id}`}>See the original conversation for context</Link></div>
 {readonly&&<p role="status">Deletion is pending. You can read this saved work, but cannot add another attempt.</p>}
 {(error||storageError)&&<div role="alert" className="error">{error||storageError}<button disabled={busy} onClick={()=>void sync()}>Retry sync / refresh</button></div>}
 {notice&&<p role="status" className="learning-notice">{notice}</p>}
 {!readonly&&<form className="retry-form" onSubmit={e=>{e.preventDefault();void save();}}><label htmlFor="retry-attempt">Your own attempt</label><textarea id="retry-attempt" ref={input} value={attempt} onChange={e=>setAttempt(e.target.value)} maxLength={20000} disabled={busy} placeholder="Write what you remember, a first step, or your reasoning…" onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!e.nativeEvent.isComposing){e.preventDefault();void save();}}}/><div className="button-row"><button className="primary" disabled={busy||!attempt.trim()}>{busy?'Saving…':'Save attempt and compare'}</button><button type="button" className="text-button" disabled={busy} onClick={()=>setRevealed(value=>!value)}>{revealed?'Hide earlier answer':'Just show earlier answer'}</button></div><p className="field-help">Your draft stays on this browser until saved. Ctrl / ⌘ + Enter saves your attempt.</p></form>}
 {readonly&&!revealed&&<button className="secondary" onClick={()=>setRevealed(true)}>Show earlier answer</button>}
 {revealed&&<section ref={comparison} tabIndex={-1} className="practice-comparison" aria-label="Compare with earlier answer"><h2>The earlier AI response</h2><p className="field-help">A reference to compare with, not an answer key. AI can make mistakes. Which steps agree with your reasoning? What would you check?</p>{data.attempts.length>0&&<div className="saved-attempt"><h3>Your latest saved retry</h3><p>{data.attempts.at(-1)?.text}</p></div>}<AnswerContent text={data.answer}/>{!readonly&&<button className="secondary" onClick={()=>{setRevealed(false);setNotice('');input.current?.focus();}}>Try again with the answer hidden</button>}</section>}
 {data.attempts.length>0&&<details className="retry-history"><summary>{data.attempts.length} previous retry {data.attempts.length===1?'attempt':'attempts'}</summary>{[...data.attempts].reverse().map(entry=><article key={entry.id}><time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time><p>{entry.text}</p></article>)}</details>}
 </section>;
}
